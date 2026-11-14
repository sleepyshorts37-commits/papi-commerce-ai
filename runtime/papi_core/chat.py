"""Messagerie interne locale PAPI, append-only et sans intégration externe."""
from __future__ import annotations

import json
import re
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from .registry import AGENTS_FILE, load_agents
from .sync_store import SyncStoreError, load_imported_records
from .local_store import LocalStoreError, append_local_record, load_local_records

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
    for field in ("sender", "recipient", "message_id", "sent_at", "message_type"):
        if not isinstance(message[field], str) or not message[field].strip():
            raise ChatError(f"Champ {field} invalide.")
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
    try:
        parsed = datetime.fromisoformat(message["sent_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ChatError("sent_at invalide.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ChatError("sent_at doit inclure un fuseau horaire.")
    if not message["message_id"].startswith("MSG-"):
        raise ChatError("Identifiant de message invalide.")
    try:
        parsed_id = UUID(message["message_id"][4:])
    except ValueError as exc:
        raise ChatError("Identifiant de message invalide.") from exc
    if parsed_id.hex.upper() != message["message_id"][4:].upper():
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
    if sqlite_db is None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = (json.dumps(message, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("Écriture incomplète du journal PAPI CHAT.")
                view = view[written:]
        finally:
            os.close(descriptor)
    else:
        try:
            append_local_record(sqlite_db, kind="message", record_id=message["message_id"],
                                event_id=message["message_id"], created_at=message["sent_at"],
                                record=message)
        except LocalStoreError as exc:
            raise ChatError(f"Écriture SQLite PAPI CHAT refusée: {exc}") from exc
    return message


def read_messages(
    *, recipient: str | None = None, limit: int = 50,
    path: Path = CHAT_FILE, agents_path: Path = AGENTS_FILE,
    import_db: Path | None = None,
) -> list[dict[str, Any]]:
    """Lit les messages locaux destinés à un agent ou diffusés à tous."""
    if not isinstance(limit, int) or not 1 <= limit <= 200:
        raise ChatError("limit doit être compris entre 1 et 200.")
    allowed = _allowed_ids(agents_path)
    if recipient is not None and recipient not in allowed:
        raise ChatError("Destinataire inconnu.")
    path = Path(path)
    messages = []
    seen_ids: set[str] = set()
    seen_messages: dict[str, dict[str, Any]] = {}
    local_messages = []
    if path.exists():
        local_messages = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(local_messages, start=1):
        if not line.strip():
            raise ChatError(f"Ligne vide interdite dans le journal PAPI CHAT ligne {number}.")
        try:
            message = json.loads(line)
            validate_message(message, agents_path)
            if message["message_id"] in seen_ids:
                raise ChatError("Identifiant de message dupliqué.")
            seen_ids.add(message["message_id"])
            seen_messages[message["message_id"]] = message
        except (json.JSONDecodeError, ChatError) as exc:
            raise ChatError(f"Message invalide à la ligne {number}: {exc}") from exc
        if recipient is None or message["recipient"] in {recipient, "all"}:
            messages.append(message)
    try:
        imported = load_imported_records(import_db, "message")
    except SyncStoreError as exc:
        raise ChatError(f"Magasin PAPI CHAT synchronisé invalide: {exc}") from exc
    for number, message in enumerate(imported, start=1):
        try:
            validate_message(message, agents_path)
            message_id = message["message_id"]
            if message_id in seen_ids:
                previous = seen_messages.get(message_id)
                if previous == message:
                    continue
                raise ChatError("Collision entre message local et message importé.")
            seen_ids.add(message_id)
            seen_messages[message_id] = message
        except (ChatError, KeyError, TypeError) as exc:
            raise ChatError(f"Message importé invalide #{number}: {exc}") from exc
        if recipient is None or message["recipient"] in {recipient, "all"}:
            messages.append(message)
    return messages[-limit:]
