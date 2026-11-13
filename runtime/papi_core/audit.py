"""Journal d'audit local chaîné, append-only par API et détectable en cas d'altération."""
from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import math
import os
import re
import stat
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SENSITIVE_KEY = re.compile(r"(password|passwd|secret|token|otp|pin|cvv|card|credential|authorization|cookie|phone|email|address|customer|client_data)", re.I)
REQUIRED = {"event_id", "occurred_at", "actor", "action", "entity_type", "entity_id", "details"}
CHAIN_FIELDS = {"previous_hash", "event_hash"}
GENESIS_HASH = "0" * 64
MAX_DETAIL_DEPTH = 8
MAX_CONTAINER_ITEMS = 100
MAX_EVENT_BYTES = 64 * 1024
MAX_INTEGER_BITS = 63


class AuditError(ValueError):
    """Événement d'audit invalide ou dangereux."""


def _check_safe(value: Any, path: str = "details", depth: int = 0) -> None:
    if depth > MAX_DETAIL_DEPTH:
        raise AuditError(f"Nesting trop profond: {path}")
    if isinstance(value, dict):
        if len(value) > MAX_CONTAINER_ITEMS:
            raise AuditError(f"Trop de champs: {path}")
        for key, child in value.items():
            if not isinstance(key, str) or SENSITIVE_KEY.search(key):
                raise AuditError(f"Champ potentiellement sensible interdit: {path}.{key}")
            _check_safe(child, f"{path}.{key}", depth + 1)
    elif isinstance(value, list):
        if len(value) > MAX_CONTAINER_ITEMS:
            raise AuditError(f"Trop d’éléments: {path}")
        for index, child in enumerate(value):
            _check_safe(child, f"{path}[{index}]", depth + 1)
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise AuditError(f"Valeur numérique non finie interdite: {path}")
    elif isinstance(value, str):
        if len(value) > 500:
            raise AuditError(f"Texte trop long: {path}")
    elif isinstance(value, int) and not isinstance(value, bool):
        if value.bit_length() > MAX_INTEGER_BITS:
            raise AuditError(f"Entier trop grand: {path}")
    elif value is not None and not isinstance(value, (bool, int, float)):
        raise AuditError(f"Type non autorisé: {path}")


def validate_event(event: dict[str, Any]) -> None:
    if not isinstance(event, dict):
        raise AuditError("L'événement doit être un objet.")
    missing = REQUIRED - event.keys()
    extra = event.keys() - REQUIRED - CHAIN_FIELDS
    if missing:
        raise AuditError(f"Champs manquants: {', '.join(sorted(missing))}")
    if extra:
        raise AuditError(f"Champs inconnus: {', '.join(sorted(extra))}")
    if bool(CHAIN_FIELDS & event.keys()) and not CHAIN_FIELDS <= event.keys():
        raise AuditError("Métadonnées de chaînage incomplètes.")
    for field in ("event_id", "actor", "action", "entity_type", "entity_id"):
        value = event[field]
        if not isinstance(value, str) or not value.strip() or len(value) > 120:
            raise AuditError(f"{field} doit être un texte non vide de 120 caractères maximum.")
    if not isinstance(event["occurred_at"], str):
        raise AuditError("occurred_at doit être une date ISO 8601.")
    try:
        parsed_at = datetime.fromisoformat(event["occurred_at"].replace("Z", "+00:00"))
        if parsed_at.tzinfo is None or parsed_at.utcoffset() is None:
            raise AuditError("occurred_at doit inclure un fuseau horaire explicite.")
    except ValueError as exc:
        raise AuditError("occurred_at n'est pas une date ISO 8601 valide.") from exc
    if not isinstance(event["details"], dict):
        raise AuditError("details doit être un objet.")
    _check_safe(event["details"])
    encoded_size = len(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"))
    if encoded_size > MAX_EVENT_BYTES:
        raise AuditError(f"Événement trop volumineux: maximum {MAX_EVENT_BYTES} octets.")
    if CHAIN_FIELDS <= event.keys():
        for field in CHAIN_FIELDS:
            value = event[field]
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
                raise AuditError(f"{field} doit être un SHA-256 hexadécimal.")


def _event_digest(event: dict[str, Any], previous_hash: str) -> str:
    canonical = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256((previous_hash + canonical).encode("utf-8")).hexdigest()


def _open_regular_file(path: Path, flags: int, mode: int = 0o600) -> int:
    """Ouvre un fichier régulier sans suivre de lien symbolique."""
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise AuditError("La plateforme ne permet pas de refuser les liens symboliques.")
    descriptor = os.open(path, flags | nofollow | getattr(os, "O_NONBLOCK", 0), mode)
    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise AuditError("Le journal et son verrou doivent être des fichiers réguliers.")
        if stat.S_IMODE(file_stat.st_mode) & 0o077:
            raise AuditError("Permissions trop ouvertes: journal et verrou doivent être privés (0600).")
        if hasattr(os, "geteuid") and file_stat.st_uid != os.geteuid():
            raise AuditError("Le journal et son verrou doivent appartenir à l'utilisateur du worker.")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


@contextmanager
def _journal_lock(path: Path) -> Iterator[None]:
    """Verrou inter-processus POSIX couvrant lecture, déduplication et ajout."""
    lock_path = path.with_name(path.name + ".lock")
    descriptor = _open_regular_file(lock_path, os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


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


def _read_verified(path: Path) -> list[dict[str, Any]]:
    try:
        descriptor = _open_regular_file(path, os.O_RDONLY)
    except FileNotFoundError:
        return []
    with os.fdopen(descriptor, "r", encoding="utf-8") as journal:
        lines = journal.read().splitlines()
    events: list[dict[str, Any]] = []
    seen: set[str] = set()
    previous_hash = GENESIS_HASH
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            raise AuditError(f"Ligne vide interdite dans le journal (ligne {line_number}).")
        try:
            event = json.loads(line)
            validate_event(event)
        except (json.JSONDecodeError, AuditError) as exc:
            raise AuditError(f"Événement invalide à la ligne {line_number}: {exc}") from exc
        if not CHAIN_FIELDS <= event.keys():
            raise AuditError(f"Événement non chaîné à la ligne {line_number}; migration explicite requise.")
        if event["event_id"] in seen:
            raise AuditError(f"Identifiant d'événement dupliqué: {event['event_id']}")
        if event["previous_hash"] != previous_hash:
            raise AuditError(f"Rupture de chaîne à la ligne {line_number}.")
        body = {key: value for key, value in event.items() if key not in CHAIN_FIELDS}
        expected_hash = _event_digest(body, previous_hash)
        if not hmac.compare_digest(event["event_hash"], expected_hash):
            raise AuditError(f"Intégrité cryptographique invalide à la ligne {line_number}.")
        seen.add(event["event_id"])
        previous_hash = event["event_hash"]
        events.append(event)
    return events


def append_event(event: dict[str, Any], path: Path) -> bool:
    """Ajoute atomiquement un événement chaîné; refuse tout journal altéré ou ancien."""
    validate_event(event)
    if CHAIN_FIELDS & event.keys():
        raise AuditError("Ne pas fournir les champs de chaînage; ils sont calculés par le journal.")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _journal_lock(path):
        existing = _read_verified(path)
        if any(item["event_id"] == event["event_id"] for item in existing):
            return False
        previous_hash = existing[-1]["event_hash"] if existing else GENESIS_HASH
        record = {**event, "previous_hash": previous_hash}
        record["event_hash"] = _event_digest(event, previous_hash)
        validate_event(record)
        payload = (json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
        descriptor = _open_regular_file(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND)
        try:
            written = 0
            while written < len(payload):
                count = os.write(descriptor, payload[written:])
                if count <= 0:
                    raise OSError("Écriture du journal d'audit interrompue.")
                written += count
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    return True


def read_events(path: Path) -> list[dict[str, Any]]:
    """Relit le journal sous verrou pour éviter toute lecture pendant un ajout."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _journal_lock(path):
        return _read_verified(path)
