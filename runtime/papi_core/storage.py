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
