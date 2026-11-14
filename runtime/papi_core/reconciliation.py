"""Aperçu déterministe et sans écriture de réconciliation inter-instances."""
from __future__ import annotations

import re
from typing import Any

from .memory import SECRET_PATTERN
from .principal import require_authenticated_agent_principal

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_AGENT_ID = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
_MESSAGE_ID = re.compile(r"^MSG-[A-F0-9]{32}$")
_MEMORY_SCOPES = {"shared", "agent", "owner"}
_MEMORY_SENSITIVITIES = {"normal", "restricted"}
_CHAT_TYPES = {"info", "task", "alert", "report"}
_MEMORY_SECRET = re.compile(
    r"(?i)\b(?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|password|passwd|secret|"
    r"token|otp|pin|cvv|authorization|cookie)\s*[:=]\s*\S+|"
    r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{20,})\b"
)
_CHAT_SECRET = re.compile(
    r"(?i)\b(?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|password|passwd|secret|"
    r"token|otp|pin|cvv|authorization|cookie)\s*[:=]\s*\S+|"
    r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}|"
    r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{20,})\b"
)


class ReconciliationError(ValueError):
    """Entrée de réconciliation invalide ou non sûre."""


def _visible_memory(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(records, list):
        raise ReconciliationError("Les mémoires doivent être fournies sous forme de liste.")
    visible = []
    seen = set()
    for row in records:
        if not isinstance(row, dict):
            raise ReconciliationError("Enregistrement mémoire invalide.")
        event_type = row.get("event_type", "remember")
        if not isinstance(event_type, str) or event_type not in {"remember", "supersede"}:
            raise ReconciliationError("Type d'événement mémoire invalide.")
        if event_type == "supersede":
            continue
        scope = row.get("scope")
        if not isinstance(scope, str) or scope not in _MEMORY_SCOPES:
            raise ReconciliationError("Portée mémoire invalide.")
        # Les mémoires privées et owner ne sont jamais candidates à la comparaison.
        if scope != "shared":
            continue
        sensitivity = row.get("sensitivity")
        if not isinstance(sensitivity, str) or sensitivity not in _MEMORY_SENSITIVITIES:
            raise ReconciliationError("Sensibilité mémoire invalide.")
        if sensitivity != "normal":
            continue
        record_id = row.get("memory_id")
        if not isinstance(record_id, str) or not _ID.fullmatch(record_id):
            raise ReconciliationError("Identifiant mémoire invalide.")
        if record_id in seen:
            raise ReconciliationError("Identifiant mémoire dupliqué dans une même source.")
        seen.add(record_id)
        title, content = row.get("title"), row.get("content")
        if (
            not isinstance(title, str) or not title.strip() or len(title) > 120
            or not isinstance(content, str) or not content.strip() or len(content) > 2000
        ):
            raise ReconciliationError("Contenu mémoire invalide.")
        if SECRET_PATTERN.search(title + "\n" + content) or _MEMORY_SECRET.search(title + "\n" + content):
            raise ReconciliationError("Contenu mémoire ressemblant à un secret refusé.")
        visible.append(row)
    return visible


def _normalise_memory_sources(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mappe la source JSONL locale vers les colonnes SQL distantes."""
    normalised = []
    for row in records:
        item = dict(row)
        source = item.get("source")
        if isinstance(source, dict):
            item.setdefault("source_type", source.get("type"))
            item.setdefault("source_id", source.get("id"))
        normalised.append(item)
    return normalised


def _visible_messages(records: list[dict[str, Any]], actor: str) -> list[dict[str, Any]]:
    if not isinstance(records, list):
        raise ReconciliationError("Les messages doivent être fournis sous forme de liste.")
    visible = []
    seen = set()
    for row in records:
        if not isinstance(row, dict):
            raise ReconciliationError("Enregistrement message invalide.")
        recipient = row.get("recipient")
        if (
            not isinstance(recipient, str)
            or (recipient != "all" and not _AGENT_ID.fullmatch(recipient))
        ):
            raise ReconciliationError("Destinataire message invalide.")
        # Un agent ne compare que les messages diffusés ou qui lui sont adressés.
        if recipient not in {"all", actor}:
            continue
        sender = row.get("sender")
        if not isinstance(sender, str) or not _AGENT_ID.fullmatch(sender):
            raise ReconciliationError("Expéditeur message invalide.")
        message_id = row.get("message_id")
        if not isinstance(message_id, str) or not _MESSAGE_ID.fullmatch(message_id):
            raise ReconciliationError("Identifiant message invalide.")
        if message_id in seen:
            raise ReconciliationError("Identifiant message dupliqué dans une même source.")
        seen.add(message_id)
        subject, body = row.get("subject"), row.get("body")
        if (
            not isinstance(subject, str) or not subject.strip() or len(subject) > 120
            or not isinstance(body, str) or not body.strip() or len(body) > 2000
        ):
            raise ReconciliationError("Contenu message invalide.")
        message_type = row.get("message_type")
        if not isinstance(message_type, str) or message_type not in _CHAT_TYPES:
            raise ReconciliationError("Type de message invalide.")
        if (
            SECRET_PATTERN.search(subject + "\n" + body)
            or _CHAT_SECRET.search(subject + "\n" + body)
        ):
            raise ReconciliationError("Contenu message ressemblant à un secret refusé.")
        visible.append(row)
    return visible


def _compare(
    local: list[dict[str, Any]],
    remote: list[dict[str, Any]],
    *,
    id_field: str,
    semantic_fields: tuple[str, ...],
    kind: str,
) -> dict[str, list[dict[str, str]]]:
    local_by_id = {row[id_field]: row for row in local}
    remote_by_id = {row[id_field]: row for row in remote}
    result = {"local_only": [], "remote_only": [], "identical": [], "conflicts": []}
    for record_id in sorted(local_by_id.keys() | remote_by_id.keys()):
        left, right = local_by_id.get(record_id), remote_by_id.get(record_id)
        item = {"type": kind, "record_id": record_id}
        if left is None:
            result["remote_only"].append(item)
        elif right is None:
            result["local_only"].append(item)
        elif all(left.get(field) == right.get(field) for field in semantic_fields):
            result["identical"].append(item)
        else:
            result["conflicts"].append(item)
    return result


def build_reconciliation_preview(
    *,
    principal: object,
    local_memory: list[dict[str, Any]],
    remote_memory: list[dict[str, Any]],
    local_messages: list[dict[str, Any]],
    remote_messages: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare explicit snapshots. Ne crée aucun client et n'effectue aucune écriture."""
    actor = require_authenticated_agent_principal(principal).agent_id
    memories = _compare(
        _normalise_memory_sources(_visible_memory(local_memory)),
        _normalise_memory_sources(_visible_memory(remote_memory)),
        id_field="memory_id",
        semantic_fields=("category", "title", "content", "source_type", "source_id",
                         "confidence", "scope", "tags", "sensitivity"),
        kind="memory",
    )
    messages = _compare(
        _visible_messages(local_messages, actor), _visible_messages(remote_messages, actor),
        id_field="message_id",
        semantic_fields=("sender", "recipient", "subject", "body", "message_type"),
        kind="message",
    )
    combined = {key: memories[key] + messages[key] for key in memories}
    counts = {key: len(value) for key, value in combined.items()}
    return {
        "mode": "preview_only",
        "writes_performed": False,
        "actor": actor,
        "counts": counts,
        "memory": memories,
        "messages": messages,
        "requires_human_review": bool(counts["conflicts"] or counts["local_only"] or counts["remote_only"]),
    }
