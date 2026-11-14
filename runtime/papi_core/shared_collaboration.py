"""Adaptateurs explicites, paginés et idempotents pour mémoire et PAPI CHAT."""
from __future__ import annotations

import base64
import json
import re
from typing import Any
from urllib.parse import quote

from .memory import CATEGORIES, SECRET_PATTERN, _safe_text
from .principal import require_authenticated_agent_principal
from .storage import StoreError

_AGENT_ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
_KEY = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
_CHAT_TYPES = {"info", "task", "alert", "report"}


class SharedCollaborationError(ValueError):
    """Données partagées invalides ou accès refusé."""


class SharedCollaborationStore:
    """Façade allowlistée ; le backend serveur et le principal sont injectés."""

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

    @staticmethod
    def _key(value: str) -> str:
        if not isinstance(value, str) or not _KEY.fullmatch(value):
            raise SharedCollaborationError("Une clé d'idempotence stable (8 à 128 caractères) est obligatoire.")
        return value

    @staticmethod
    def _cursor(value: str | None) -> tuple[str, str] | None:
        if value is None:
            return None
        if not isinstance(value, str) or len(value) > 512:
            raise SharedCollaborationError("Curseur invalide.")
        try:
            raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
            data = json.loads(raw.decode("utf-8"))
            stamp, record_id = data["t"], data["i"]
            if not isinstance(stamp, str) or not isinstance(record_id, str) or not stamp or not record_id:
                raise ValueError
            return stamp, record_id
        except (ValueError, KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SharedCollaborationError("Curseur invalide.") from exc

    @staticmethod
    def _encode_cursor(stamp: str, record_id: str) -> str:
        raw = json.dumps({"t": stamp, "i": record_id}, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    def _insert_once(self, table: str, payload: dict[str, Any], key: str) -> dict[str, Any]:
        rows = self._store._request(
            "POST", f"{table}?on_conflict=idempotency_key",
            {**payload, "idempotency_key": key},
            prefer="resolution=ignore-duplicates,return=representation",
        )
        if isinstance(rows, list) and len(rows) == 1:
            return rows[0]
        existing = self._store._request(
            "GET", f"{table}?idempotency_key=eq.{quote(key, safe='')}&select=*"
        )
        if not isinstance(existing, list) or len(existing) != 1:
            raise StoreError("Résultat de l'opération idempotente introuvable.")
        row = existing[0]
        if any(row.get(name) != value for name, value in payload.items()):
            raise SharedCollaborationError("Cette clé d'idempotence est déjà utilisée pour un contenu différent.")
        return row

    def remember(self, *, principal: object, category: str, title: str,
                 content: str, source_type: str, source_id: str,
                 idempotency_key: str, confidence: float = 0.8,
                 scope: str = "shared", tags: list[str] | None = None) -> dict[str, Any]:
        actor = self._actor(principal)
        key = self._key(idempotency_key)
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
            "created_at": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
            "actor": actor, "category": category, "title": title, "content": content,
            "source_type": source_type, "source_id": source_id,
            "confidence": float(confidence), "scope": scope,
            "tags": clean_tags, "sensitivity": "normal",
        }
        return self._insert_once("papi_memory_events", event, key)

    def search_memory(self, *, principal: object, query: str = "",
                      category: str | None = None, limit: int = 20,
                      cursor: str | None = None) -> dict[str, Any]:
        actor = self._actor(principal)
        if not isinstance(query, str) or len(query) > 120:
            raise SharedCollaborationError("Requête invalide.")
        if category is not None and category not in CATEGORIES - {"decision"}:
            raise SharedCollaborationError("Catégorie invalide.")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise SharedCollaborationError("limit doit être compris entre 1 et 100.")
        position = self._cursor(cursor)
        fields = "event_id,memory_id,event_type,created_at,actor,category,title,content,source_type,source_id,confidence,scope,tags,sensitivity,target_memory_id,reason"
        base = f"papi_memory_events?select={fields}&order=created_at.desc,event_id.desc&limit={limit + 1}"
        seek = ""
        if position:
            stamp, event_id = position
            encoded_stamp = quote(stamp, safe="")
            seek = f"&or=(created_at.lt.{encoded_stamp},and(created_at.eq.{encoded_stamp},event_id.lt.{quote(event_id, safe='')}))"
        shared_path = base + "&scope=eq.shared&event_type=eq.remember" + seek
        private_path = base + f"&scope=eq.agent&actor=eq.{quote(actor, safe='')}&event_type=eq.remember" + seek
        shared = self._store._request("GET", shared_path)
        private = self._store._request("GET", private_path)
        if not isinstance(shared, list) or not isinstance(private, list):
            raise StoreError("Réponse mémoire partagée invalide.")
        rows = sorted(shared + private,
                      key=lambda item: (item.get("created_at", ""), item.get("event_id", "")),
                      reverse=True)
        has_more = len(rows) > limit
        page = rows[:limit]
        if page:
            ids = ",".join(quote(str(row["memory_id"]), safe="") for row in page)
            superseded = self._store._request(
                "GET", f"papi_memory_events?select=target_memory_id&event_type=eq.supersede&target_memory_id=in.({ids})"
            )
            if not isinstance(superseded, list):
                raise StoreError("Réponse d'archivage mémoire invalide.")
            hidden = {row.get("target_memory_id") for row in superseded}
        else:
            hidden = set()
        terms = query.casefold().split()
        results = []
        for row in page:
            if row.get("memory_id") in hidden or (category and row.get("category") != category):
                continue
            haystack = " ".join([row.get("title", ""), row.get("content", "")] + row.get("tags", [])).casefold()
            if all(term in haystack for term in terms):
                results.append({key: value for key, value in row.items() if key != "event_type"})
        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = self._encode_cursor(last["created_at"], last["event_id"])
        return {"items": results, "next_cursor": next_cursor}

    def send_message(self, *, principal: object, recipient: str, subject: str,
                     body: str, idempotency_key: str,
                     message_type: str = "info") -> dict[str, Any]:
        actor = self._actor(principal)
        key = self._key(idempotency_key)
        if recipient != "all" and (not isinstance(recipient, str) or not _AGENT_ID.fullmatch(recipient)):
            raise SharedCollaborationError("Destinataire invalide.")
        if not isinstance(subject, str) or not 1 <= len(subject.strip()) <= 120:
            raise SharedCollaborationError("Sujet invalide.")
        if not isinstance(body, str) or not 1 <= len(body.strip()) <= 2000:
            raise SharedCollaborationError("Corps invalide.")
        if SECRET_PATTERN.search(subject + "\n" + body) or message_type not in _CHAT_TYPES:
            raise SharedCollaborationError("Secret potentiel ou type de message interdit.")
        from datetime import datetime, timezone
        from uuid import uuid4
        message = {
            "message_id": "MSG-" + uuid4().hex.upper(),
            "sent_at": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
            "sender": actor, "recipient": recipient, "subject": subject.strip(),
            "body": body.strip(), "message_type": message_type,
        }
        return self._insert_once("papi_chat_messages", message, key)

    def read_messages(self, *, principal: object, limit: int = 50,
                      cursor: str | None = None) -> dict[str, Any]:
        actor = self._actor(principal)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
            raise SharedCollaborationError("limit doit être compris entre 1 et 200.")
        position = self._cursor(cursor)
        seek = ""
        if position:
            stamp, message_id = position
            encoded_stamp = quote(stamp, safe="")
            seek = f"&and=(or=(sent_at.lt.{encoded_stamp},and(sent_at.eq.{encoded_stamp},message_id.lt.{quote(message_id, safe='')})))"
        path = (
            "papi_chat_messages?select=message_id,sent_at,sender,recipient,subject,body,message_type"
            f"&or=(recipient.eq.all,recipient.eq.{quote(actor, safe='')})"
            f"&order=sent_at.desc,message_id.desc&limit={limit + 1}{seek}"
        )
        rows = self._store._request("GET", path)
        if not isinstance(rows, list):
            raise StoreError("Réponse de messagerie partagée invalide.")
        has_more = len(rows) > limit
        items = rows[:limit]
        next_cursor = None
        if has_more and items:
            last = items[-1]
            next_cursor = self._encode_cursor(last["sent_at"], last["message_id"])
        return {"items": items, "next_cursor": next_cursor}
