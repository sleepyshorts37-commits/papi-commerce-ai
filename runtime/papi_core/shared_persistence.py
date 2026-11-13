"""Adaptateurs Supabase explicites pour la mémoire et PAPI CHAT.

Ces adaptateurs ne sont pas branchés aux API locales par défaut. Ils exigent
un SupabaseStore injecté par le backend de confiance et une identité agent
authentifiée pour toute lecture mémoire.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

from .principal import require_authenticated_agent_principal
from .storage import StoreError, SupabaseStore


class SharedPersistenceError(ValueError):
    """Entrée distante invalide ou réponse de stockage inattendue."""


def _rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise StoreError("Réponse inattendue du stockage partagé.")
    return value


class SharedMemoryAdapter:
    """Persistance append-only mémoire ; aucun branchement automatique."""

    def __init__(self, store: SupabaseStore):
        if not isinstance(store, SupabaseStore):
            raise TypeError("Un SupabaseStore de confiance est obligatoire.")
        self._store = store

    def append_event(self, event: dict[str, Any]) -> None:
        if not isinstance(event, dict) or event.get("event_type") not in {"remember", "supersede"}:
            raise SharedPersistenceError("Événement mémoire invalide.")
        actor = event.get("actor")
        if not isinstance(actor, str) or not actor or len(actor) > 100:
            raise SharedPersistenceError("Acteur mémoire invalide.")
        common = {
            "event_id": event.get("event_id"),
            "memory_id": event.get("memory_id") or event.get("target_memory_id"),
            "event_type": event["event_type"],
            "created_at": event.get("created_at"),
            "actor": actor,
        }
        if event["event_type"] == "remember":
            source = event.get("source")
            if not isinstance(source, dict):
                raise SharedPersistenceError("Source mémoire invalide.")
            common.update({
                "category": event.get("category"), "title": event.get("title"),
                "content": event.get("content"), "source_type": source.get("type"),
                "source_id": source.get("id"), "confidence": event.get("confidence"),
                "scope": event.get("scope"), "tags": event.get("tags", []),
                "sensitivity": event.get("sensitivity"),
            })
        else:
            common.update({
                "target_memory_id": event.get("target_memory_id"),
                "reason": event.get("reason"),
            })
        rows = self._store.request("POST", "papi_memory_events", common,
                                   prefer="return=representation")
        if not isinstance(rows, list) or len(rows) != 1:
            raise StoreError("Insertion de l'événement mémoire non confirmée.")

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

        # Le filtrage d'accès est fait côté PostgreSQL avant pagination.
        actor_q = quote(actor, safe="")
        access = f"or=(scope.eq.shared,and(scope.eq.agent,actor.eq.{actor_q}))"
        terms = query.casefold().split()
        events: list[dict[str, Any]] = []
        offset = 0
        superseded: set[str] = set()
        while True:
            params = (
                "select=event_id,memory_id,event_type,created_at,actor,category,title,content,"
                "source_type,source_id,confidence,scope,tags,sensitivity,target_memory_id,reason"
                f"&{access}&order=created_at.desc,event_id.desc&limit=100&offset={offset}"
            )
            if category:
                params += f"&category=eq.{quote(category, safe='')}"
            batch = _rows(self._store.request("GET", f"papi_memory_events?{params}"))
            if not batch:
                break
            for row in batch:
                if row.get("event_type") == "supersede":
                    superseded.add(str(row.get("target_memory_id")))
                elif row.get("event_type") == "remember":
                    events.append(row)
            if len(batch) < 100:
                break
            offset += len(batch)

        results = []
        for row in reversed(events):
            if str(row.get("memory_id")) in superseded:
                continue
            source = {"type": row.get("source_type"), "id": row.get("source_id")}
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
                "content": row["content"], "source": source,
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
        rows = self._store.request(
            "POST", "papi_chat_messages", message, prefer="return=representation"
        )
        if not isinstance(rows, list) or len(rows) != 1:
            raise StoreError("Insertion du message non confirmée.")

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
