"""Journal d'audit local append-only, sans secrets ni données sensibles."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SENSITIVE_KEY = re.compile(r"(password|passwd|secret|token|otp|pin|cvv|card|credential|authorization|cookie|phone|email|address|customer|client_data)", re.I)
REQUIRED = {"event_id", "occurred_at", "actor", "action", "entity_type", "entity_id", "details"}


class AuditError(ValueError):
    """Événement d'audit invalide ou dangereux."""


def _check_safe(value: Any, path: str = "details") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or SENSITIVE_KEY.search(key):
                raise AuditError(f"Champ potentiellement sensible interdit: {path}.{key}")
            _check_safe(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_safe(child, f"{path}[{index}]")
    elif isinstance(value, str):
        if len(value) > 500:
            raise AuditError(f"Texte trop long: {path}")
    elif value is not None and not isinstance(value, (bool, int, float)):
        raise AuditError(f"Type non autorisé: {path}")


def validate_event(event: dict[str, Any]) -> None:
    if not isinstance(event, dict):
        raise AuditError("L'événement doit être un objet.")
    missing = REQUIRED - event.keys()
    extra = event.keys() - REQUIRED
    if missing:
        raise AuditError(f"Champs manquants: {', '.join(sorted(missing))}")
    if extra:
        raise AuditError(f"Champs inconnus: {', '.join(sorted(extra))}")
    for field in ("event_id", "actor", "action", "entity_type", "entity_id"):
        value = event[field]
        if not isinstance(value, str) or not value.strip() or len(value) > 120:
            raise AuditError(f"{field} doit être un texte non vide de 120 caractères maximum.")
    if not isinstance(event["occurred_at"], str):
        raise AuditError("occurred_at doit être une date ISO 8601.")
    try:
        datetime.fromisoformat(event["occurred_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise AuditError("occurred_at n'est pas une date ISO 8601 valide.") from exc
    if not isinstance(event["details"], dict):
        raise AuditError("details doit être un objet.")
    _check_safe(event["details"])


def new_event(*, event_id: str, actor: str, action: str, entity_type: str,
              entity_id: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    event = {
        "event_id": event_id,
        "occurred_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "actor": actor,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "details": details or {},
    }
    validate_event(event)
    return event


def append_event(event: dict[str, Any], path: Path) -> bool:
    """Ajoute un événement avec verrou inter-processus et déduplication atomique."""
    import fcntl

    validate_event(event)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        os.lseek(descriptor, 0, os.SEEK_SET)
        chunks = []
        while True:
            chunk = os.read(descriptor, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        existing_bytes = b"".join(chunks)
        if existing_bytes and not existing_bytes.endswith(b"\n"):
            raise AuditError("Journal incomplet : dernière ligne tronquée, écriture refusée.")
        seen = set()
        for line_number, line in enumerate(existing_bytes.decode("utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                existing = json.loads(line)
                validate_event(existing)
            except (json.JSONDecodeError, UnicodeDecodeError, AuditError) as exc:
                raise AuditError(f"Journal corrompu à la ligne {line_number}.") from exc
            event_id = existing["event_id"]
            if event_id in seen:
                raise AuditError(f"Identifiant d'événement dupliqué dans le journal: {event_id}")
            seen.add(event_id)
        if event["event_id"] in seen:
            return False
        payload = (json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        original_size = len(existing_bytes)
        try:
            view = memoryview(payload)
            written = 0
            while written < len(payload):
                written += os.write(descriptor, view[written:])
            os.fsync(descriptor)
        except Exception:
            os.ftruncate(descriptor, original_size)
            os.fsync(descriptor)
            raise
        return True
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def read_events(path: Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise AuditError("Journal incomplet : dernière ligne tronquée.")
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AuditError("Journal invalide : encodage UTF-8 incorrect.") from exc
    events = []
    seen = set()
    for line_number, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            validate_event(event)
        except (json.JSONDecodeError, AuditError) as exc:
            raise AuditError(f"Événement invalide à la ligne {line_number}: {exc}") from exc
        if event["event_id"] in seen:
            raise AuditError(f"Identifiant d'événement dupliqué: {event['event_id']}")
        seen.add(event["event_id"])
        events.append(event)
    return events
