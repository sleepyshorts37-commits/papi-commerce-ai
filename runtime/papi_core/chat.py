"""Messagerie interne locale PAPI, append-only et sans intégration externe."""
from __future__ import annotations

import json
import re
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .registry import AGENTS_FILE, load_agents

CHAT_FILE = Path(__file__).resolve().parents[2] / "data" / "chat" / "messages.jsonl"
SECRET_PATTERN = re.compile(
    r"(?i)(api[_ -]?key|access[_ -]?token|refresh[_ -]?token|password|passwd|secret|"
    r"otp|pin|cvv|authorization)\s*[:=]\s*\S+|"
    r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{20,})\b"
)


class ChatError(ValueError):
    """Message interne invalide ou destinataire inconnu."""


def _allowed_ids(agents_path: Path) -> set[str]:
    return set(load_agents(agents_path)) | {"owner", "system"}


def validate_message(message: dict[str, Any], agents_path: Path = AGENTS_FILE) -> None:
    if not isinstance(message, dict):
        raise ChatError("Le message doit être un objet.")
    required = {"message_id", "sent_at", "sender", "recipient", "subject", "body", "message_type"}
    if set(message) != required:
        raise ChatError("Structure du message invalide.")
    allowed = _allowed_ids(agents_path)
    if message["sender"] not in allowed:
        raise ChatError("Expéditeur inconnu.")
    recipient = message["recipient"]
    if recipient != "all" and recipient not in allowed:
        raise ChatError("Destinataire inconnu.")
    if not isinstance(message["subject"], str) or not 1 <= len(message["subject"].strip()) <= 120:
        raise ChatError("Le sujet doit contenir entre 1 et 120 caractères.")
    if not isinstance(message["body"], str) or not 1 <= len(message["body"].strip()) <= 2000:
        raise ChatError("Le corps doit contenir entre 1 et 2000 caractères.")
    if SECRET_PATTERN.search(message["subject"] + "\n" + message["body"]):
        raise ChatError("Contenu ressemblant à un secret d'authentification interdit.")
    if message["message_type"] not in {"info", "task", "alert", "report"}:
        raise ChatError("Type de message invalide.")
    if not isinstance(message["sent_at"], str):
        raise ChatError("sent_at doit être une date ISO 8601.")
    try:
        datetime.fromisoformat(message["sent_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ChatError("sent_at invalide.") from exc
    if not isinstance(message["message_id"], str) or not message["message_id"].startswith("MSG-"):
        raise ChatError("Identifiant de message invalide.")


def send_message(
    *, sender: str, recipient: str, subject: str, body: str,
    message_type: str = "info", path: Path = CHAT_FILE,
    agents_path: Path = AGENTS_FILE,
) -> dict[str, Any]:
    """Enregistre un message local; n'envoie rien sur Internet."""
    message = {
        "message_id": f"MSG-{uuid4().hex.upper()}",
        "sent_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "sender": sender,
        "recipient": recipient,
        "subject": subject,
        "body": body,
        "message_type": message_type,
    }
    validate_message(message, agents_path)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(message, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(descriptor, payload)
    finally:
        os.close(descriptor)
    return message


def read_messages(
    *, recipient: str | None = None, limit: int = 50,
    path: Path = CHAT_FILE, agents_path: Path = AGENTS_FILE,
) -> list[dict[str, Any]]:
    """Lit les messages locaux destinés à un agent ou diffusés à tous."""
    if not isinstance(limit, int) or not 1 <= limit <= 200:
        raise ChatError("limit doit être compris entre 1 et 200.")
    allowed = _allowed_ids(agents_path)
    if recipient is not None and recipient not in allowed:
        raise ChatError("Destinataire inconnu.")
    path = Path(path)
    if not path.exists():
        return []
    messages = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            validate_message(message, agents_path)
        except (json.JSONDecodeError, ChatError) as exc:
            raise ChatError(f"Message invalide à la ligne {number}: {exc}") from exc
        if recipient is None or message["recipient"] in {recipient, "all"}:
            messages.append(message)
    return messages[-limit:]
