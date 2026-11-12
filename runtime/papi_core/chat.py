"""Messagerie interne locale PAPI, append-only et messages authentifiés Ed25519."""
from __future__ import annotations

import json
import re
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .chat_authorization import ChatAuthorizationError, authorize_send, require_permission
from .agent_identity_auth import authenticate_agent_request, AgentIdentityAuthenticationError
from .identity_ed25519 import (
    DEFAULT_PRIVATE_DIR, DEFAULT_PUBLIC_REGISTRY, DEFAULT_REPLAY_DB,
    Ed25519IdentityError, sign_ed25519_request, verify_ed25519_request,
    verify_ed25519_signature,
)
from .registry import AGENTS_FILE, load_agents

CHAT_FILE = Path(__file__).resolve().parents[2] / "data" / "chat" / "messages.jsonl"
SECRET_PATTERN = re.compile(
    r"(?i)(api[_ -]?key|access[_ -]?token|refresh[_ -]?token|password|passwd|secret|"
    r"otp|pin|cvv|authorization)\s*[:=]\s*\S+|"
    r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{20,})\b"
)
MESSAGE_ID_PATTERN = re.compile(r"^MSG-[A-F0-9]{32}$")


class ChatError(ValueError):
    """Message interne invalide ou authentification refusée."""


def _allowed_ids(agents_path: Path) -> set[str]:
    return set(load_agents(agents_path)) | {"owner", "system"}


def _validate_message_fields(message: dict[str, Any], agents_path: Path) -> None:
    if not isinstance(message, dict):
        raise ChatError("Le message doit être un objet.")
    required = {"message_id", "sent_at", "sender", "recipient", "subject", "body", "message_type"}
    if set(message) != required:
        raise ChatError("Structure du message invalide.")
    for field in required:
        if not isinstance(message[field], str):
            raise ChatError(f"Le champ {field} doit être une chaîne de caractères.")
    allowed = _allowed_ids(agents_path)
    if message["sender"] not in allowed:
        raise ChatError("Expéditeur inconnu.")
    recipient = message["recipient"]
    if recipient != "all" and recipient not in allowed:
        raise ChatError("Destinataire inconnu.")
    if not 1 <= len(message["subject"].strip()) <= 120:
        raise ChatError("Le sujet doit contenir entre 1 et 120 caractères.")
    if not 1 <= len(message["body"].strip()) <= 2000:
        raise ChatError("Le corps doit contenir entre 1 et 2000 caractères.")
    if SECRET_PATTERN.search(message["subject"] + "\n" + message["body"]):
        raise ChatError("Contenu ressemblant à un secret d'authentification interdit.")
    if message["message_type"] not in {"info", "task", "alert", "report"}:
        raise ChatError("Type de message invalide.")
    if not MESSAGE_ID_PATTERN.fullmatch(message["message_id"]):
        raise ChatError("Identifiant de message invalide.")
    try:
        parsed = datetime.fromisoformat(message["sent_at"].replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timezone absente")
    except ValueError as exc:
        raise ChatError("sent_at doit être une date ISO 8601 avec fuseau horaire.") from exc


def validate_message(
    record: dict[str, Any], agents_path: Path = AGENTS_FILE,
    public_registry_path: Path = DEFAULT_PUBLIC_REGISTRY,
) -> None:
    """Valide les champs et authentifie la preuve Ed25519 sans consommer le nonce."""
    if not isinstance(record, dict) or set(record) != {"message", "auth"}:
        raise ChatError("Enregistrement signé invalide.")
    message, envelope = record["message"], record["auth"]
    _validate_message_fields(message, agents_path)
    if not isinstance(envelope, dict) or envelope.get("agent_id") != message["sender"]:
        raise ChatError("L'identité signataire ne correspond pas à l'expéditeur.")
    if envelope.get("payload") != message:
        raise ChatError("Le contenu du message ne correspond pas au contenu signé.")
    try:
        verify_ed25519_signature(envelope, public_registry_path)
    except Ed25519IdentityError as exc:
        raise ChatError(f"Authentification Ed25519 refusée : {exc}") from exc


def send_message(
    *, sender: str, recipient: str, subject: str, body: str,
    message_type: str = "info", path: Path = CHAT_FILE,
    agents_path: Path = AGENTS_FILE, identities_path: Path | None = None,
    private_key_path: Path | None = None,
    key_version: int = 1, public_registry_path: Path = DEFAULT_PUBLIC_REGISTRY,
    replay_db_path: Path = DEFAULT_REPLAY_DB,
) -> dict[str, Any]:
    """Signe, authentifie puis enregistre localement un message ; aucun envoi réseau."""
    message = {
        "message_id": f"MSG-{uuid4().hex.upper()}",
        "sent_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "sender": sender, "recipient": recipient, "subject": subject,
        "body": body, "message_type": message_type,
    }
    _validate_message_fields(message, agents_path)
    try:
        authorize_send(sender, recipient, agents_path)
    except ChatAuthorizationError as exc:
        raise ChatError(f"Envoi interdit : {exc}") from exc
    key_path = Path(private_key_path) if private_key_path is not None else DEFAULT_PRIVATE_DIR / (sender + ".ed25519.pem")
    try:
        envelope = sign_ed25519_request(sender, message, key_path, key_version=key_version)
        # Freshness + nonce uniqueness are enforced exactly once, at ingestion.
        if sender in load_agents(agents_path):
            authenticate_agent_request(
                envelope, agents_path=agents_path,
                **({"identities_path": identities_path} if identities_path is not None else {}),
                public_registry_path=public_registry_path, replay_db=replay_db_path,
            )
        else:
            # Owner/system principals retain their separately defined trust path.
            verify_ed25519_request(envelope, public_registry_path, replay_db_path)
    except (Ed25519IdentityError, AgentIdentityAuthenticationError) as exc:
        raise ChatError(f"Envoi refusé : {exc}") from exc
    record = {"message": message, "auth": envelope}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(descriptor, payload)
    finally:
        os.close(descriptor)
    return record


def read_messages(
    *, reader: str, limit: int = 50,
    path: Path = CHAT_FILE, agents_path: Path = AGENTS_FILE,
    identities_path: Path | None = None,
    private_key_path: Path | None = None, key_version: int = 1,
    public_registry_path: Path = DEFAULT_PUBLIC_REGISTRY,
    replay_db_path: Path = DEFAULT_REPLAY_DB,
) -> list[dict[str, Any]]:
    """Lit la boîte autorisée après authentification Ed25519 du lecteur."""
    if not isinstance(reader, str) or not reader:
        raise ChatError("Lecteur invalide.")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 200:
        raise ChatError("limit doit être compris entre 1 et 200.")
    key_path = Path(private_key_path) if private_key_path is not None else DEFAULT_PRIVATE_DIR / (reader + ".ed25519.pem")
    try:
        require_permission(reader, "chat.read", agents_path)
        challenge = sign_ed25519_request(
            reader, {"action": "chat.read", "reader": reader}, key_path,
            key_version=key_version,
        )
        if reader in load_agents(agents_path):
            authenticate_agent_request(
                challenge, agents_path=agents_path,
                **({"identities_path": identities_path} if identities_path is not None else {}),
                public_registry_path=public_registry_path, replay_db=replay_db_path,
            )
        else:
            verify_ed25519_request(challenge, public_registry_path, replay_db_path)
        can_read_all = reader == "owner"
    except (ChatAuthorizationError, Ed25519IdentityError, AgentIdentityAuthenticationError) as exc:
        raise ChatError(f"Lecture interdite : {exc}") from exc
    path = Path(path)
    if not path.exists():
        return []
    messages = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            validate_message(record, agents_path, public_registry_path)
        except (json.JSONDecodeError, ChatError) as exc:
            raise ChatError(f"Message invalide à la ligne {number}: {exc}") from exc
        message = record["message"]
        if can_read_all or message["recipient"] in {reader, "all"}:
            messages.append(record)
    return messages[-limit:]
