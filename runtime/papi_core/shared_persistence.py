"""Adaptateurs Supabase explicites pour la mémoire et PAPI CHAT.

Ces adaptateurs ne sont pas branchés aux API locales par défaut. Ils exigent
un SupabaseStore injecté par le backend de confiance et une identité agent
authentifiée pour toute lecture ou écriture mémoire.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote
from uuid import UUID

from .principal import require_authenticated_agent_principal
from .storage import StoreError, SupabaseStore


class SharedPersistenceError(ValueError):
    """Entrée distante invalide ou réponse de stockage inattendue."""


MAX_MEMORY_SCAN = 5000
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")
_AGENT = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
_MESSAGE_ID = re.compile(r"^MSG-[A-F0-9]{32}$")
_SECRET = re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{16,}|\bBearer\s+[A-Za-z0-9._~-]{12,}|\b(?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|password|passwd|secret|otp|pin|cvv|authorization)\s*[:=]\s*\S+)", re.I)


def _rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise StoreError("Réponse inattendue du stockage partagé.")
    return value


def _comparison_value(field: str, value: Any) -> Any:
    if field in {"created_at", "sent_at"} and isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            return value
    return value


def _append_idempotently(store: SupabaseStore, table: str, payload: dict[str, Any], key: str) -> None:
    """Insère une fois ; une répétition identique est un succès, une collision échoue."""
    rows = store.request(
        "POST", table, payload,
        prefer="resolution=ignore-duplicates,return=representation",
    )
    if not isinstance(rows, list):
        raise StoreError("Réponse inattendue après insertion partagée.")
    if len(rows) == 1:
        return
    if rows:
        raise StoreError("Réponse inattendue après insertion partagée.")
    identity = quote(str(payload[key]), safe="")
    existing = _rows(store.request(
        "GET", f"{table}?select=*&{key}=eq.{identity}&limit=1"
    ))
    if len(existing) != 1 or any(
        _comparison_value(field, existing[0].get(field))
        != _comparison_value(field, value)
        for field, value in payload.items()
    ):
        raise StoreError("Collision d'identifiant : l'enregistrement existant diffère du nouvel envoi.")


def _valid_timestamp(value: Any, field: str) -> None:
    if not isinstance(value, str):
        raise SharedPersistenceError(f"{field} doit être une date ISO 8601.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SharedPersistenceError(f"{field} invalide.") from exc
    if parsed.tzinfo is None:
        raise SharedPersistenceError(f"{field} doit inclure un fuseau horaire.")


def _valid_uuid(value: Any, field: str) -> None:
    if not isinstance(value, str) or not _UUID.fullmatch(value):
        raise SharedPersistenceError(f"{field} doit être un UUID valide.")
    try:
        UUID(value)
    except ValueError as exc:
        raise SharedPersistenceError(f"{field} doit être un UUID valide.") from exc


class SharedMemoryAdapter:
    """Persistance append-only mémoire ; aucun branchement automatique."""

    def __init__(self, store: SupabaseStore):
        if not isinstance(store, SupabaseStore):
            raise TypeError("Un SupabaseStore de confiance est obligatoire.")
        self._store = store

    def append_event(self, event: dict[str, Any], *, principal: object) -> None:
        authenticated = require_authenticated_agent_principal(principal)
        if not isinstance(event, dict) or event.get("event_type") not in {"remember", "supersede"}:
            raise SharedPersistenceError("Événement mémoire invalide.")
        actor = event.get("actor")
        if not isinstance(actor, str) or not _AGENT.fullmatch(actor) or actor != authenticated.agent_id:
            raise PermissionError("L'acteur de l'événement doit correspondre à l'agent authentifié.")
        _valid_uuid(event.get("event_id"), "event_id")
        _valid_timestamp(event.get("created_at"), "created_at")
        if event["event_type"] == "remember":
            _valid_uuid(event.get("memory_id"), "memory_id")
            source = event.get("source")
            if not isinstance(source, dict):
                raise SharedPersistenceError("Source mémoire invalide.")
            category = event.get("category")
            if category not in {"fact", "project", "result", "procedure", "lesson"}:
                raise SharedPersistenceError("Catégorie mémoire invalide.")
            for key, maximum in (("title", 120), ("content", 2000)):
                value = event.get(key)
                if not isinstance(value, str) or not value.strip() or len(value) > maximum:
                    raise SharedPersistenceError(f"{key} invalide.")
                if _SECRET.search(value):
                    raise SharedPersistenceError(f"Contenu ressemblant à un secret interdit dans {key}.")
            for key, maximum in (("type", 40), ("id", 120)):
                value = source.get(key)
                if not isinstance(value, str) or not value.strip() or len(value) > maximum:
                    raise SharedPersistenceError(f"source.{key} invalide.")
            confidence = event.get("confidence")
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                raise SharedPersistenceError("confidence doit être comprise entre 0 et 1.")
            if event.get("scope") not in {"shared", "agent"} or event.get("sensitivity") != "normal":
                raise SharedPersistenceError("Portée ou sensibilité mémoire interdite.")
            tags = event.get("tags", [])
            if not isinstance(tags, list) or len(tags) > 10 or any(
                not isinstance(tag, str) or not tag.strip() or len(tag) > 30 for tag in tags
            ):
                raise SharedPersistenceError("Liste de tags invalide.")
            common = {
                "event_id": event["event_id"], "memory_id": event["memory_id"],
                "event_type": "remember", "created_at": event["created_at"], "actor": actor,
                "category": category, "title": event["title"], "content": event["content"],
                "source_type": source["type"], "source_id": source["id"],
                "confidence": float(confidence), "scope": event["scope"],
                "tags": tags, "sensitivity": "normal",
            }
        else:
            target = event.get("target_memory_id")
            _valid_uuid(target, "target_memory_id")
            reason = event.get("reason")
            if not isinstance(reason, str) or not reason.strip() or len(reason) > 240:
                raise SharedPersistenceError("reason invalide.")
            # Un agent ne peut archiver que sa propre mémoire privée ou une
            # mémoire partagée. La vérification est faite côté serveur avant écriture.
            visible = _rows(self._store.request(
                "GET",
                "papi_memory_events?select=memory_id,actor,scope"
                f"&memory_id=eq.{quote(target, safe='')}&event_type=eq.remember&limit=100"
            ))
            if not any(
                row.get("memory_id") == target
                and (row.get("actor") == actor or row.get("scope") == "shared")
                for row in visible
            ):
                raise PermissionError("Mémoire cible inexistante ou non accessible pour cet agent.")
            common = {
                "event_id": event["event_id"], "memory_id": target,
                "event_type": "supersede", "created_at": event["created_at"],
                "actor": actor, "target_memory_id": target, "reason": reason,
            }
        _append_idempotently(self._store, "papi_memory_events", common, "event_id")

    def search(
        self, *, principal: object, query: str = "", category: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        authenticated = require_authenticated_agent_principal(principal)
        actor = authenticated.agent_id
        if not isinstance(query, str) or len(query) > 120:
            raise SharedPersistenceError("Requête mémoire invalide.")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise SharedPersistenceError("limit doit être compris entre 1 et 100.")
        if category is not None and category not in {"fact", "project", "result", "procedure", "lesson"}:
            raise SharedPersistenceError("Catégorie mémoire invalide.")

        # Inclure les événements supersede même lors d'une recherche par catégorie :
        # le filtrage de catégorie est donc appliqué localement après le calcul d'état.
        actor_q = quote(actor, safe="")
        access = f"or=(scope.eq.shared,and(scope.eq.agent,actor.eq.{actor_q}),event_type.eq.supersede)"
        terms = query.casefold().split()
        events: list[dict[str, Any]] = []
        offset = 0
        supersede_events: list[dict[str, Any]] = []
        scanned = 0
        while True:
            page_size = min(100, MAX_MEMORY_SCAN - scanned)
            params = (
                "select=event_id,memory_id,event_type,created_at,actor,category,title,content,"
                "source_type,source_id,confidence,scope,tags,sensitivity,target_memory_id"
                f"&{access}&order=created_at.desc,event_id.desc&limit={page_size}&offset={offset}"
            )
            batch = _rows(self._store.request("GET", f"papi_memory_events?{params}"))
            if not batch:
                break
            scanned += len(batch)
            for row in batch:
                if row.get("event_type") == "supersede":
                    supersede_events.append(row)
                elif row.get("event_type") == "remember":
                    events.append(row)
            if len(batch) < page_size:
                break
            if scanned >= MAX_MEMORY_SCAN:
                raise StoreError("Recherche mémoire trop volumineuse ; réduire le périmètre avant de réessayer.")
            offset += len(batch)

        # Un supersede ne peut masquer que la mémoire privée de son auteur
        # ou une mémoire partagée visible par cet agent.
        visible_shared_ids = {
            str(row.get("memory_id")) for row in events if row.get("scope") == "shared"
        }
        superseded = {
            str(item.get("target_memory_id"))
            for item in supersede_events
            if item.get("actor") == actor
            or str(item.get("target_memory_id")) in visible_shared_ids
        }

        results = []
        for row in reversed(events):
            if str(row.get("memory_id")) in superseded:
                continue
            if category is not None and row.get("category") != category:
                continue
            searchable = " ".join([
                str(row.get("title", "")), str(row.get("content", "")),
                " ".join(row.get("tags") or []),
            ]).casefold()
            if terms and not all(term in searchable for term in terms):
                continue
            results.append({
                "event_id": row["event_id"], "memory_id": row["memory_id"],
                "created_at": row["created_at"], "actor": row["actor"],
                "category": row["category"], "title": row["title"],
                "content": row["content"],
                "source": {"type": row.get("source_type"), "id": row.get("source_id")},
                "confidence": float(row["confidence"]), "scope": row["scope"],
                "tags": row.get("tags") or [], "sensitivity": row["sensitivity"],
            })
        return results[-limit:][::-1]


class SharedChatAdapter:
    """Boîte de réception distante ; lecture limitée à l'agent authentifié."""

    def __init__(self, store: SupabaseStore):
        if not isinstance(store, SupabaseStore):
            raise TypeError("Un SupabaseStore de confiance est obligatoire.")
        self._store = store

    def append_message(self, message: dict[str, Any]) -> None:
        if not isinstance(message, dict):
            raise SharedPersistenceError("Message invalide.")
        fields = ("message_id", "sent_at", "sender", "recipient", "subject", "body", "message_type")
        if set(message) != set(fields):
            raise SharedPersistenceError("Structure du message invalide.")
        if not isinstance(message["message_id"], str) or not _MESSAGE_ID.fullmatch(message["message_id"]):
            raise SharedPersistenceError("Identifiant de message invalide.")
        _valid_timestamp(message["sent_at"], "sent_at")
        if not isinstance(message["sender"], str) or not _AGENT.fullmatch(message["sender"]):
            raise SharedPersistenceError("Expéditeur invalide.")
        if not isinstance(message["recipient"], str) or (
            message["recipient"] != "all" and not _AGENT.fullmatch(message["recipient"])
        ):
            raise SharedPersistenceError("Destinataire invalide.")
        if not isinstance(message["subject"], str) or not 1 <= len(message["subject"].strip()) <= 120:
            raise SharedPersistenceError("Sujet invalide.")
        if not isinstance(message["body"], str) or not 1 <= len(message["body"].strip()) <= 2000:
            raise SharedPersistenceError("Corps du message invalide.")
        if _SECRET.search(message["subject"] + "\n" + message["body"]):
            raise SharedPersistenceError("Contenu ressemblant à un secret d’authentification interdit.")
        if message["message_type"] not in {"info", "task", "alert", "report"}:
            raise SharedPersistenceError("Type de message invalide.")
        _append_idempotently(self._store, "papi_chat_messages", message, "message_id")

    def read_messages(self, *, principal: object, limit: int = 50) -> list[dict[str, Any]]:
        authenticated = require_authenticated_agent_principal(principal)
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 200:
            raise SharedPersistenceError("limit doit être compris entre 1 et 200.")
        actor = quote(authenticated.agent_id, safe="")
        query = (
            "select=message_id,sent_at,sender,recipient,subject,body,message_type"
            f"&or=(recipient.eq.{actor},recipient.eq.all)"
            f"&order=sent_at.desc,message_id.desc&limit={limit}"
        )
        rows = _rows(self._store.request("GET", f"papi_chat_messages?{query}"))
        return list(reversed(rows))
