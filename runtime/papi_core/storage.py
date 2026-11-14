"""Persistance Supabase/PostgREST avec contrôle optimiste et transitions atomiques."""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .audit import validate_event


class StoreError(RuntimeError):
    """Erreur de configuration, de transport ou de cohérence du stockage."""


class SupabaseStore:
    """Stockage distant. Aucun secret n'est codé en dur ni journalisé."""

    def __init__(self, url: str | None = None, key: str | None = None, timeout: int = 15):
        self.url = (url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.key = key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_KEY", "")
        self.timeout = timeout
        if not self.url.startswith("https://") or not self.key:
            raise StoreError("Configurer SUPABASE_URL (HTTPS) et SUPABASE_SERVICE_ROLE_KEY dans l'environnement serveur.")

    def _request(self, method: str, path: str, payload: Any = None, prefer: str | None = None):
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        request = Request(f"{self.url}/rest/v1/{path}", data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else None
        except HTTPError as exc:
            raise StoreError(f"Supabase a répondu HTTP {exc.code}.") from exc
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise StoreError(f"Échec de communication avec Supabase ({type(exc).__name__}).") from exc

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        rows = self._request("GET", f"papi_tasks?id=eq.{quote(task_id, safe='')}&select=task,version")
        if not isinstance(rows, list):
            raise StoreError("Réponse inattendue du stockage.")
        if not rows:
            return None
        return rows[0]

    def save_task(self, task: dict[str, Any], *, expected_version: int | None = None) -> int:
        """Insère une tâche (version 1) ou la met à jour si la version attendue correspond."""
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id:
            raise StoreError("La tâche doit avoir un identifiant.")
        if expected_version is None:
            rows = self._request(
                "POST", "papi_tasks",
                {"id": task_id, "task": task, "version": 1},
                prefer="return=representation",
            )
            if not isinstance(rows, list) or not rows:
                raise StoreError("Insertion non confirmée.")
            return int(rows[0]["version"])
        if not isinstance(expected_version, int) or expected_version < 1:
            raise StoreError("Version attendue invalide.")
        rows = self._request(
            "PATCH",
            f"papi_tasks?id=eq.{quote(task_id, safe='')}&version=eq.{expected_version}",
            {"task": task, "version": expected_version + 1},
            prefer="return=representation",
        )
        if not isinstance(rows, list) or len(rows) != 1:
            raise StoreError("Conflit de version : tâche modifiée ailleurs ou introuvable. Relire avant de réessayer.")
        return int(rows[0]["version"])

    def append_audit_event(self, event: dict[str, Any]) -> bool:
        validate_event(event)
        rows = self._request("POST", "papi_audit_events", event, prefer="return=representation")
        return isinstance(rows, list) and len(rows) == 1

    def commit_task_change(
        self, task: dict[str, Any], event: dict[str, Any], *, expected_version: int
    ) -> int:
        """Enregistre tâche + audit dans une seule transaction PostgreSQL via RPC."""
        validate_event(event)
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id or event["entity_type"] != "task" or event["entity_id"] != task_id:
            raise StoreError("La tâche et l'événement d'audit doivent désigner la même mission.")
        if not isinstance(expected_version, int) or expected_version < 1:
            raise StoreError("Version attendue invalide.")
        result = self._request(
            "POST",
            "rpc/papi_commit_task_change",
            {
                "p_task_id": task_id,
                "p_expected_version": expected_version,
                "p_task": task,
                "p_event": event,
            },
        )
        if not isinstance(result, int) or result != expected_version + 1:
            raise StoreError("La transaction n'a pas retourné une nouvelle version valide.")
        return result

    def transition_and_save(
        self, task_id: str, new_status: str, *, actor: str,
        expected_version: int, reason: str = "", evidence: list[str] | None = None,
    ) -> tuple[dict[str, Any], int]:
        """Relit, vérifie la version, calcule la transition puis la valide atomiquement."""
        from .state_machine import TransitionError, transition_task

        current = self.get_task(task_id)
        if not current or current.get("version") != expected_version:
            raise StoreError("Conflit de version ou mission introuvable ; relire avant de réessayer.")
        try:
            updated, event = transition_task(
                current["task"], new_status, actor=actor, reason=reason, evidence=evidence
            )
        except (KeyError, TransitionError) as exc:
            raise StoreError(f"Transition refusée : {exc}") from exc
        version = self.commit_task_change(updated, event, expected_version=expected_version)
        return updated, version

    def approve_and_save(
        self, task_id: str, *, approver: str, decision: str,
        expected_version: int, reason: str = "",
    ) -> tuple[dict[str, Any], int]:
        """Enregistre une approbation explicite sans déclencher la mission."""
        from .state_machine import TransitionError, approve_task

        current = self.get_task(task_id)
        if not current or current.get("version") != expected_version:
            raise StoreError("Conflit de version ou mission introuvable ; relire avant de réessayer.")
        try:
            updated, event = approve_task(
                current["task"], approver=approver, decision=decision, reason=reason
            )
        except (KeyError, TransitionError) as exc:
            raise StoreError(f"Approbation refusée : {exc}") from exc
        version = self.commit_task_change(updated, event, expected_version=expected_version)
        return updated, version


    @staticmethod
    def _collaboration_idempotency_key(kind: str, identifier: str) -> str:
        import hashlib
        return hashlib.sha256(f"papi:{kind}:{identifier}".encode("utf-8")).hexdigest()

    def sync_memory_event(self, event: dict[str, Any], *, principal: object) -> dict[str, Any]:
        """Append one authenticated memory event; retries are idempotent."""
        from .principal import require_authenticated_agent_principal

        actor = require_authenticated_agent_principal(principal).agent_id
        if not isinstance(event, dict) or event.get("actor") != actor:
            raise StoreError("L'acteur mémoire ne correspond pas à l'identité authentifiée.")
        event_type = event.get("event_type")
        if event_type == "remember":
            source = event.get("source")
            if (event.get("scope") not in {"shared", "agent"} or event.get("sensitivity") != "normal"
                    or event.get("category") not in {"fact", "project", "result", "procedure", "lesson"}
                    or not isinstance(source, dict)):
                raise StoreError("Événement mémoire non conforme au contrat partagé.")
            if event["scope"] == "agent" and event["actor"] != actor:
                raise StoreError("Une mémoire privée ne peut être publiée que par son auteur.")
            row = {
                "event_id": event.get("event_id"), "memory_id": event.get("memory_id"),
                "event_type": "remember", "created_at": event.get("created_at"), "actor": actor,
                "category": event.get("category"), "title": event.get("title"),
                "content": event.get("content"), "source_type": source.get("type"),
                "source_id": source.get("id"), "confidence": event.get("confidence"),
                "scope": event.get("scope"), "tags": event.get("tags", []),
                "sensitivity": "normal", "idempotency_key": self._collaboration_idempotency_key("memory", str(event.get("event_id"))),
            }
        elif event_type == "supersede":
            row = {
                "event_id": event.get("event_id"), "memory_id": event.get("target_memory_id"),
                "event_type": "supersede", "created_at": event.get("created_at"),
                "actor": actor, "target_memory_id": event.get("target_memory_id"),
                "reason": event.get("reason"), "tags": [],
                "idempotency_key": self._collaboration_idempotency_key("memory", str(event.get("event_id"))),
            }
        else:
            raise StoreError("Type d'événement mémoire invalide.")
        if not isinstance(row["event_id"], str) or not isinstance(row["created_at"], str):
            raise StoreError("Identifiant ou horodatage mémoire absent.")
        rows = self._request("POST", "papi_memory_events?on_conflict=idempotency_key",
                             row, prefer="resolution=ignore-duplicates,return=representation")
        if rows is None:
            raise StoreError("Réponse inattendue lors de la synchronisation mémoire.")
        return {"synced": isinstance(rows, list) and len(rows) == 1,
                "duplicate": isinstance(rows, list) and len(rows) == 0,
                "event_id": row["event_id"]}

    def sync_chat_message(self, message: dict[str, Any], *, principal: object,
                          agents_path=None) -> dict[str, Any]:
        """Append an authenticated internal chat message; no external delivery."""
        from pathlib import Path
        from .principal import require_authenticated_agent_principal
        from .chat import validate_message, AGENTS_FILE

        actor = require_authenticated_agent_principal(principal).agent_id
        if not isinstance(message, dict) or message.get("sender") != actor:
            raise StoreError("L'expéditeur ne correspond pas à l'identité authentifiée.")
        try:
            validate_message(message, Path(agents_path) if agents_path else AGENTS_FILE)
        except (ValueError, KeyError) as exc:
            raise StoreError("Message interne invalide.") from exc
        row = {key: message[key] for key in
               ("message_id", "sent_at", "sender", "recipient", "subject", "body", "message_type")}
        row["idempotency_key"] = self._collaboration_idempotency_key("chat", message["message_id"])
        rows = self._request("POST", "papi_chat_messages?on_conflict=idempotency_key",
                             row, prefer="resolution=ignore-duplicates,return=representation")
        if rows is None:
            raise StoreError("Réponse inattendue lors de la synchronisation chat.")
        return {"synced": isinstance(rows, list) and len(rows) == 1,
                "duplicate": isinstance(rows, list) and len(rows) == 0,
                "message_id": message["message_id"]}

    def list_memory_events(self, *, principal: object, limit: int = 50) -> list[dict[str, Any]]:
        """Read shared plus own-agent memory only; never reads owner/restricted scope."""
        from urllib.parse import quote
        from .principal import require_authenticated_agent_principal

        actor = require_authenticated_agent_principal(principal).agent_id
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise StoreError("Limite mémoire invalide.")
        query = ("papi_memory_events?select=event_id,memory_id,event_type,created_at,actor,category,title,content,"
                 "source_type,source_id,confidence,scope,tags,sensitivity,target_memory_id,reason"
                 "&or=(and(scope.eq.shared),and(scope.eq.agent,actor.eq." + quote(actor, safe="") + "))"
                 "&order=created_at.desc,event_id.desc&limit=" + str(limit))
        rows = self._request("GET", query)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise StoreError("Réponse mémoire distante invalide.")
        return rows

    def list_chat_messages(self, *, principal: object, limit: int = 50) -> list[dict[str, Any]]:
        """Read broadcasts and messages addressed to the authenticated agent."""
        from urllib.parse import quote
        from .principal import require_authenticated_agent_principal

        actor = require_authenticated_agent_principal(principal).agent_id
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 200:
            raise StoreError("Limite chat invalide.")
        query = ("papi_chat_messages?select=message_id,sent_at,sender,recipient,subject,body,message_type"
                 "&or=(recipient.eq.all,recipient.eq." + quote(actor, safe="") + ")"
                 "&order=sent_at.desc,message_id.desc&limit=" + str(limit))
        rows = self._request("GET", query)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise StoreError("Réponse chat distante invalide.")
        return rows

    @staticmethod
    def _decode_collaboration_cursor(cursor: str | None) -> tuple[str, str] | None:
        import base64
        if cursor is None:
            return None
        if not isinstance(cursor, str) or len(cursor) > 512:
            raise StoreError("Curseur de synchronisation invalide.")
        try:
            decoded = base64.urlsafe_b64decode(cursor.encode("ascii") + b"=" * (-len(cursor) % 4)).decode("utf-8")
            timestamp, identifier = decoded.split("|", 1)
            if not timestamp or not identifier:
                raise ValueError("empty cursor")
            return timestamp, identifier
        except (ValueError, UnicodeError) as exc:
            raise StoreError("Curseur de synchronisation invalide.") from exc

    @staticmethod
    def _encode_collaboration_cursor(timestamp: str, identifier: str) -> str:
        import base64
        raw = f"{timestamp}|{identifier}".encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    def page_memory_events(self, *, principal: object, limit: int = 50,
                           cursor: str | None = None) -> dict[str, Any]:
        from urllib.parse import quote
        from .principal import require_authenticated_agent_principal
        actor = require_authenticated_agent_principal(principal).agent_id
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise StoreError("Limite mémoire invalide.")
        query = ("papi_memory_events?select=event_id,memory_id,event_type,created_at,actor,category,title,content,"
                 "source_type,source_id,confidence,scope,tags,sensitivity,target_memory_id,reason"
                 "&or=(and(scope.eq.shared),and(scope.eq.agent,actor.eq." + quote(actor, safe="") + "))")
        decoded = self._decode_collaboration_cursor(cursor)
        if decoded:
            ts, identifier = decoded
            query += "&or=(created_at.lt." + quote(ts, safe=":.-+") + ",and(created_at.eq." + quote(ts, safe=":.-+") + ",event_id.lt." + quote(identifier, safe="") + "))"
        query += "&order=created_at.desc,event_id.desc&limit=" + str(limit + 1)
        rows = self._request("GET", query)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise StoreError("Réponse mémoire distante invalide.")
        has_more = len(rows) > limit
        items = rows[:limit]
        next_cursor = None
        if has_more and items:
            last = items[-1]
            next_cursor = self._encode_collaboration_cursor(last["created_at"], last["event_id"])
        return {"items": items, "next_cursor": next_cursor}

    def page_chat_messages(self, *, principal: object, limit: int = 50,
                           cursor: str | None = None) -> dict[str, Any]:
        from urllib.parse import quote
        from .principal import require_authenticated_agent_principal
        actor = require_authenticated_agent_principal(principal).agent_id
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 200:
            raise StoreError("Limite chat invalide.")
        query = ("papi_chat_messages?select=message_id,sent_at,sender,recipient,subject,body,message_type"
                 "&or=(recipient.eq.all,recipient.eq." + quote(actor, safe="") + ")")
        decoded = self._decode_collaboration_cursor(cursor)
        if decoded:
            ts, identifier = decoded
            query += "&or=(sent_at.lt." + quote(ts, safe=":.-+") + ",and(sent_at.eq." + quote(ts, safe=":.-+") + ",message_id.lt." + quote(identifier, safe="") + "))"
        query += "&order=sent_at.desc,message_id.desc&limit=" + str(limit + 1)
        rows = self._request("GET", query)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise StoreError("Réponse chat distante invalide.")
        has_more = len(rows) > limit
        items = rows[:limit]
        next_cursor = None
        if has_more and items:
            last = items[-1]
            next_cursor = self._encode_collaboration_cursor(last["sent_at"], last["message_id"])
        return {"items": items, "next_cursor": next_cursor}

    def sync_worker_event(self, event: dict[str, Any], *, expected_version: int) -> dict[str, Any]:
        """Persist one worker event through the atomic, idempotent PostgreSQL RPC."""
        from .worker_store import DOMAINS, _reject_secrets

        if not isinstance(event, dict) or event.get("domain") not in DOMAINS:
            raise StoreError("Événement worker invalide.")
        if not isinstance(expected_version, int) or isinstance(expected_version, bool) or expected_version < 0:
            raise StoreError("Version attendue invalide.")
        payload = event.get("payload")
        if not isinstance(payload, dict):
            raise StoreError("Payload worker invalide.")
        _reject_secrets(payload)
        arguments = {
            "p_domain": event["domain"],
            "p_record_id": event["record_id"],
            "p_expected_version": expected_version,
            "p_event_id": event["event_id"],
            "p_idempotency_key": event["idempotency_key"],
            "p_source_event_id": event["source_event_id"],
            "p_event_type": event["event_type"],
            "p_actor": event["actor"],
            "p_payload": payload,
            "p_occurred_at": event["occurred_at"],
        }
        result = self._request("POST", "rpc/papi_sync_worker_record", arguments)
        if not isinstance(result, dict) or not isinstance(result.get("duplicate"), bool):
            raise StoreError("Réponse invalide de la synchronisation worker.")
        version = result.get("record_version")
        if not isinstance(version, int) or version < 1:
            raise StoreError("Version worker absente de la réponse Supabase.")
        return result

    def list_worker_records(self, domain: str, *, limit: int = 500) -> list[dict[str, Any]]:
        """Read one allowlisted worker domain; never returns credentials or raw DB rows."""
        from .worker_store import DOMAINS, _reject_secrets

        if domain not in DOMAINS or not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000:
            raise StoreError("Paramètres de lecture worker invalides.")
        query = (
            "papi_worker_records?domain=eq." + quote(domain, safe="")
            + "&select=domain,record_id,payload,version,source_event_id,updated_at"
            + "&order=updated_at.desc&limit=" + str(limit)
        )
        rows = self._request("GET", query)
        if not isinstance(rows, list):
            raise StoreError("Réponse inattendue du registre worker.")
        output = []
        id_fields = {
            "platform_candidate": "platform_id",
            "human_handoff": "handoff_id",
            "profitability_result": "offer_id",
        }
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("payload"), dict):
                raise StoreError("Enregistrement worker mal formé.")
            payload = dict(row["payload"])
            _reject_secrets(payload)
            payload.setdefault(id_fields[domain], row.get("record_id"))
            output.append(payload)
        return output
