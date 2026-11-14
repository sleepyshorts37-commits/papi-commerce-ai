"""Adaptateurs explicites pour la mémoire et PAPI CHAT partagés.

Aucun client réseau n'est créé ici : le store serveur doit être injecté par
l'appelant après authentification. Les journaux JSONL locaux restent inchangés.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

from .memory import CATEGORIES, SECRET_PATTERN, MemoryError, _safe_text
from .principal import require_authenticated_agent_principal
from .storage import StoreError

_AGENT_ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
_CHAT_TYPES = {"info", "task", "alert", "report"}


class SharedCollaborationError(ValueError):
    """Données partagées invalides ou accès refusé."""


class SharedCollaborationStore:
    """Façade allowlistée sur SupabaseStore, avec identité obligatoire."""

    def __init__(self, *, store: Any):
        if store is None or not callable(getattr(store, "_request", None)):
            raise SharedCollaborationError("Un store serveur compatible doit être injecté.")
        self._store = store

    @staticmethod
    def _actor(principal: object) -> str:
        actor = require_authenticated_agent_principal(principal).agent_id
        if not _AGENT_ID.fullmatch(actor):
            raise SharedCollaborationError("Identité agent invalide.")
        return actor

    def remember(self, *, principal: object, category: str, title: str,
                 content: str, source_type: str, source_id: str,
                 confidence: float = 0.8, scope: str = "shared",
                 tags: list[str] | None = None) -> dict[str, Any]:
        actor = self._actor(principal)
        if category not in CATEGORIES - {"decision"} or scope not in {"shared", "agent"}:
            raise SharedCollaborationError("Catégorie ou portée non autorisée.")
        title = _safe_text(title, "title", 120)
        content = _safe_text(content, "content", 2000)
        source_type = _safe_text(source_type, "source_type", 40)
        source_id = _safe_text(source_id, "source_id", 120)
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise SharedCollaborationError("confidence invalide.")
        if not isinstance(tags, (list, type(None))) or len(tags or []) > 10:
            raise SharedCollaborationError("10 tags maximum.")
        clean_tags = [_safe_text(tag, "tag", 30) for tag in (tags or [])]
        from datetime import datetime, timezone
        from uuid import uuid4
        event = {
            "event_id": str(uuid4()), "memory_id": str(uuid4()),
            "event_type": "remember",
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "actor": actor, "category": category, "title": title, "content": content,
            "source_type": source_type, "source_id": source_id,
            "confidence": float(confidence), "scope": scope,
            "tags": clean_tags, "sensitivity": "normal",
        }
        rows = self._store._request("POST", "papi_memory_events", event,
                                    prefer="return=representation")
        if not isinstance(rows, list) or len(rows) != 1:
            raise StoreError("Insertion mémoire partagée non confirmée.")
        return rows[0]

    def search_memory(self, *, principal: object, query: str = "",
                      category: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        actor = self._actor(principal)
        if not isinstance(query, str) or len(query) > 120:
            raise SharedCollaborationError("Requête invalide.")
        if category is not None and category not in CATEGORIES - {"decision"}:
            raise SharedCollaborationError("Catégorie invalide.")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise SharedCollaborationError("limit doit être compris entre 1 et 100.")
        fields = "event_id,memory_id,event_type,created_at,actor,category,title,content,source_type,source_id,confidence,scope,tags,sensitivity,target_memory_id,reason"
        base = f"papi_memory_events?select={fields}&order=created_at.desc&limit=200"
        shared = self._store._request("GET", base + "&scope=eq.shared&event_type=eq.remember")
        private = self._store._request(
            "GET", base + f"&scope=eq.agent&actor=eq.{quote(actor, safe='')}&event_type=eq.remember"
        )
        if not isinstance(shared, list) or not isinstance(private, list):
            raise StoreError("Réponse mémoire partagée invalide.")
        rows = shared + private
        superseded = self._store._request(
            "GET", "papi_memory_events?select=target_memory_id&event_type=eq.supersede&limit=1000"
        )
        if not isinstance(superseded, list):
            raise StoreError("Réponse d'archivage mémoire invalide.")
        hidden = {row.get("target_memory_id") for row in superseded}
        terms = query.casefold().split()
        results = []
        for row in sorted(rows, key=lambda item: item.get("created_at", ""), reverse=True):
            if row.get("memory_id") in hidden or (category and row.get("category") != category):
                continue
            haystack = " ".join([row.get("title", ""), row.get("content", "")] + row.get("tags", [])).casefold()
            if all(term in haystack for term in terms):
                results.append({key: value for key, value in row.items() if key != "event_type"})
            if len(results) == limit:
                break
        return results

    def send_message(self, *, principal: object, recipient: str, subject: str,
                     body: str, message_type: str = "info") -> dict[str, Any]:
        actor = self._actor(principal)
        if recipient != "all" and (not isinstance(recipient, str) or not _AGENT_ID.fullmatch(recipient)):
            raise SharedCollaborationError("Destinataire invalide.")
        if not isinstance(subject, str) or not 1 <= len(subject.strip()) <= 120:
            raise SharedCollaborationError("Sujet invalide.")
        if not isinstance(body, str) or not 1 <= len(body.strip()) <= 2000:
            raise SharedCollaborationError("Corps invalide.")
        if SECRET_PATTERN.search(subject + "\\n" + body) or message_type not in _CHAT_TYPES:
            raise SharedCollaborationError("Secret potentiel ou type de message interdit.")
        from datetime import datetime, timezone
        from uuid import uuid4
        message = {
            "message_id": "MSG-" + uuid4().hex.upper(),
            "sent_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sender": actor, "recipient": recipient, "subject": subject.strip(),
            "body": body.strip(), "message_type": message_type,
        }
        rows = self._store._request("POST", "papi_chat_messages", message,
                                    prefer="return=representation")
        if not isinstance(rows, list) or len(rows) != 1:
            raise StoreError("Insertion du message partagé non confirmée.")
        return rows[0]

    def read_messages(self, *, principal: object, limit: int = 50) -> list[dict[str, Any]]:
        actor = self._actor(principal)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
            raise SharedCollaborationError("limit doit être compris entre 1 et 200.")
        path = (
            "papi_chat_messages?select=message_id,sent_at,sender,recipient,subject,body,message_type"
            f"&or=(recipient.eq.all,recipient.eq.{quote(actor, safe='')})"
            f"&order=sent_at.desc,message_id.desc&limit={limit}"
        )
        rows = self._store._request("GET", path)
        if not isinstance(rows, list):
            raise StoreError("Réponse de messagerie partagée invalide.")
        return rows
