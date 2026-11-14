"""Mémoire partagée locale, traçable et append-only pour PAPI."""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .principal import require_authenticated_agent_principal
from .sync_store import SyncStoreError, load_imported_records
from .local_store import LocalStoreError, append_local_record, load_local_records

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "memory" / "events.jsonl"
CATEGORIES = {"fact", "decision", "project", "result", "procedure", "lesson"}
SCOPES = {"shared", "agent", "owner"}
SENSITIVITIES = {"normal", "restricted"}
SECRET_PATTERN = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{16,}|"
    r"\bBearer\s+[A-Za-z0-9._~-]{12,}|\b(?:otp|pin|cvv)\s*[:=]?\s*\d{3,8}\b)",
    re.I,
)
SENSITIVE_KEY = re.compile(
    r"(password|passwd|secret|token|otp|pin|cvv|card|credential|authorization|cookie|"
    r"phone|email|address|customer|client_data|birth|passport|national_id)",
    re.I,
)


class MemoryError(ValueError):
    """Entrée de mémoire invalide, inaccessible ou corrompue."""


def _safe_text(value: Any, field: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise MemoryError(f"{field} doit être un texte non vide de {limit} caractères maximum.")
    if SECRET_PATTERN.search(value):
        raise MemoryError(f"Contenu potentiellement secret interdit dans {field}.")
    return value.strip()


def _safe_tree(value: Any, path: str = "content") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or SENSITIVE_KEY.search(key):
                raise MemoryError(f"Champ potentiellement sensible interdit: {path}.{key}")
            _safe_tree(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _safe_tree(child, f"{path}[{index}]")
    elif isinstance(value, str):
        if len(value) > 2000 or SECRET_PATTERN.search(value):
            raise MemoryError(f"Texte trop long ou potentiellement secret: {path}")
    elif value is not None and not isinstance(value, (bool, int, float)):
        raise MemoryError(f"Type non autorisé: {path}")


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _validate_event(event: Any, number: int) -> None:
    """Validate the complete persisted event shape before any consumer uses it."""
    if not isinstance(event, dict) or event.get("event_type") not in {"remember", "supersede"}:
        raise MemoryError(f"Événement mémoire invalide ligne {number}.")
    required_common = ("event_id", "created_at", "actor")
    if any(not isinstance(event.get(key), str) or not event[key].strip() for key in required_common):
        raise MemoryError(f"Identité ou date d'événement invalide ligne {number}.")
    try:
        parsed = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise MemoryError(f"Date d'événement invalide ligne {number}.") from exc
    if parsed.tzinfo is None:
        raise MemoryError(f"Date sans fuseau horaire ligne {number}.")
    if event["event_type"] == "remember":
        required = ("memory_id", "category", "title", "content", "source", "confidence", "scope", "tags", "sensitivity")
        if any(key not in event for key in required):
            raise MemoryError(f"Événement remember incomplet ligne {number}.")
        if (not isinstance(event["memory_id"], str) or not event["memory_id"].strip()
                or not isinstance(event["category"], str) or event["category"] not in CATEGORIES
                or not isinstance(event["scope"], str) or event["scope"] not in SCOPES
                or not isinstance(event["sensitivity"], str) or event["sensitivity"] not in SENSITIVITIES
                or not isinstance(event["title"], str) or not event["title"].strip()
                or len(event["title"]) > 120 or not isinstance(event["content"], str)
                or not event["content"].strip() or len(event["content"]) > 2000
                or not isinstance(event["source"], dict)
                or any(not isinstance(event["source"].get(k), str) or not event["source"][k].strip()
                       for k in ("type", "id"))
                or isinstance(event["confidence"], bool)
                or not isinstance(event["confidence"], (int, float))
                or not 0 <= event["confidence"] <= 1
                or not isinstance(event["tags"], list) or len(event["tags"]) > 10
                or any(not isinstance(tag, str) or not tag.strip() or len(tag) > 30 for tag in event["tags"])):
            raise MemoryError(f"Champs remember invalides ligne {number}.")
        _safe_tree({"title": event["title"], "content": event["content"], "source": event["source"], "tags": event["tags"]})
    else:
        if any(not isinstance(event.get(key), str) or not event[key].strip()
               for key in ("target_memory_id", "reason")):
            raise MemoryError(f"Événement supersede incomplet ligne {number}.")
        _safe_text(event["reason"], "reason", 240)


def _read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events = []
    seen_events: set[str] = set()
    seen_memories: set[str] = set()
    remembered: set[str] = set()
    superseded: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise MemoryError(f"Ligne vide interdite dans le journal mémoire ligne {number}.")
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MemoryError(f"Journal mémoire corrompu ligne {number}.") from exc
        _validate_event(event, number)
        event_id = event["event_id"]
        if event_id in seen_events:
            raise MemoryError(f"Identifiant d'événement dupliqué ligne {number}.")
        seen_events.add(event_id)
        if event["event_type"] == "remember":
            memory_id = event["memory_id"]
            if memory_id in seen_memories:
                raise MemoryError(f"Identifiant mémoire dupliqué ligne {number}.")
            seen_memories.add(memory_id)
            remembered.add(memory_id)
        else:
            target = event["target_memory_id"]
            if target not in remembered or target in superseded:
                raise MemoryError(f"Référence d'archivage inconnue ou répétée ligne {number}.")
            superseded.add(target)
        events.append(event)
    return events


def _append(event: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(event, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("Écriture incomplète du journal mémoire.")
            view = view[written:]
    finally:
        os.close(fd)


def remember_fact(
    *, principal: object, category: str, title: str, content: str,
    source_type: str, source_id: str, confidence: float = 0.8,
    scope: str = "shared", tags: list[str] | None = None,
    sensitivity: str = "normal", path: Path = DEFAULT_PATH,
    sqlite_db: Path | None = None,
) -> dict[str, Any]:
    """Ajoute un fait traçable ; ne modifie jamais une entrée existante."""
    authenticated = require_authenticated_agent_principal(principal)
    actor = authenticated.agent_id
    title = _safe_text(title, "title", 120)
    content = _safe_text(content, "content", 2000)
    source_type = _safe_text(source_type, "source_type", 40)
    source_id = _safe_text(source_id, "source_id", 120)
    if category not in CATEGORIES or scope not in SCOPES or sensitivity not in SENSITIVITIES:
        raise MemoryError("Catégorie, portée ou sensibilité invalide.")
    if category == "decision":
        raise MemoryError("Un agent authentifié ne peut pas enregistrer une décision officielle.")
    if scope == "owner":
        raise MemoryError("La mémoire owner exige une authentification propriétaire distincte.")
    if sensitivity != "normal":
        raise MemoryError("Les données restreintes ne sont pas admises dans cette mémoire.")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise MemoryError("confidence doit être comprise entre 0 et 1.")
    if not isinstance(tags, (list, type(None))) or len(tags or []) > 10:
        raise MemoryError("10 tags maximum.")
    clean_tags = [_safe_text(tag, "tag", 30) for tag in (tags or [])]
    event = {
        "event_id": str(uuid.uuid4()), "event_type": "remember",
        "memory_id": str(uuid.uuid4()), "created_at": _timestamp(),
        "actor": actor, "category": category, "title": title, "content": content,
        "source": {"type": source_type, "id": source_id},
        "confidence": float(confidence), "scope": scope,
        "tags": clean_tags, "sensitivity": sensitivity,
    }
    if sqlite_db is None:
        _append(event, Path(path))
    else:
        try:
            append_local_record(sqlite_db, kind="memory", record_id=event["memory_id"],
                                event_id=event["event_id"], created_at=event["created_at"], record=event)
        except LocalStoreError as exc:
            raise MemoryError(f"Écriture SQLite mémoire refusée: {exc}") from exc
    return {key: value for key, value in event.items() if key != "event_type"}


def search_memory(
    *, principal: object, query: str = "", category: str | None = None,
    scope: str | None = None, limit: int = 20, path: Path = DEFAULT_PATH,
    import_db: Path | None = None, sqlite_db: Path | None = None,
) -> list[dict[str, Any]]:
    """Recherche locale ; les entrées privées ne sont visibles que dans leur portée."""
    authenticated = require_authenticated_agent_principal(principal)
    actor = authenticated.agent_id
    if not isinstance(query, str) or len(query) > 120:
        raise MemoryError("Requête invalide.")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise MemoryError("limit doit être compris entre 1 et 100.")
    if category is not None and category not in CATEGORIES:
        raise MemoryError("Catégorie invalide.")
    if scope is not None and scope not in SCOPES:
        raise MemoryError("Portée invalide.")
    events = _read_events(Path(path))
    try:
        operational = load_local_records(sqlite_db, "memory")
        imported = load_imported_records(import_db, "memory")
    except SyncStoreError as exc:
        raise MemoryError(f"Magasin de mémoire synchronisée invalide: {exc}") from exc
    except LocalStoreError as exc:
        raise MemoryError(f"Magasin SQLite mémoire invalide: {exc}") from exc
    known_events = {event["event_id"]: event for event in events}
    known_memories = {event.get("memory_id"): event for event in events if event.get("event_type") == "remember"}
    for event in operational:
        _validate_event(event, 0)
        prior = known_events.get(event["event_id"])
        if prior is not None:
            if prior != event:
                raise MemoryError("Collision entre mémoire JSONL et mémoire SQLite.")
            continue
        known_events[event["event_id"]] = event
        events.append(event)
    for event in imported:
        _validate_event(event, 0)
        if (event.get("event_type") != "remember" or event.get("scope") != "shared"
                or event.get("sensitivity") != "normal" or event.get("category") == "decision"):
            raise MemoryError("Contenu mémoire importé hors du périmètre partagé autorisé.")
        previous = known_events.get(event["event_id"])
        previous_memory = known_memories.get(event["memory_id"])
        if previous is not None or previous_memory is not None:
            if previous == event and previous_memory == event:
                continue
            raise MemoryError("Collision entre mémoire locale et mémoire importée.")
        known_events[event["event_id"]] = event
        known_memories[event["memory_id"]] = event
        events.append(event)
    superseded = {e.get("target_memory_id") for e in events if e["event_type"] == "supersede"}
    terms = query.casefold().split()
    results = []
    for event in events:
        if event["event_type"] != "remember" or event["memory_id"] in superseded:
            continue
        if event["scope"] == "owner":
            continue
        if event["scope"] == "agent" and actor != event["actor"]:
            continue
        if category and event["category"] != category:
            continue
        if scope and event["scope"] != scope:
            continue
        searchable = (event["title"] + " " + event["content"] + " " + " ".join(event["tags"])).casefold()
        if terms and not all(term in searchable for term in terms):
            continue
        results.append({key: value for key, value in event.items() if key != "event_type"})
    return results[-limit:][::-1]


def supersede_memory(
    *, memory_id: str, principal: object, reason: str, path: Path = DEFAULT_PATH,
    sqlite_db: Path | None = None,
) -> bool:
    """Archive logiquement une entrée par événement ; l'historique reste intact."""
    memory_id = _safe_text(memory_id, "memory_id", 120)
    authenticated = require_authenticated_agent_principal(principal)
    actor = authenticated.agent_id
    reason = _safe_text(reason, "reason", 240)
    events = _read_events(Path(path))
    try:
        events.extend(load_local_records(sqlite_db, "memory"))
    except LocalStoreError as exc:
        raise MemoryError(f"Magasin SQLite mémoire invalide: {exc}") from exc
    target = next((e for e in events if e["event_type"] == "remember" and e["memory_id"] == memory_id), None)
    if target is None:
        raise MemoryError("Entrée mémoire introuvable.")
    if target["category"] == "decision" or target["scope"] == "owner":
        raise MemoryError("Un agent ne peut pas archiver une mémoire réservée au propriétaire.")
    if target["scope"] == "agent" and actor != target["actor"]:
        raise MemoryError("Un agent ne peut pas archiver la mémoire privée d’un autre agent.")
    if any(e.get("target_memory_id") == memory_id for e in events if e["event_type"] == "supersede"):
        return False
    event = {
        "event_id": str(uuid.uuid4()), "event_type": "supersede",
        "target_memory_id": memory_id, "created_at": _timestamp(),
        "actor": actor, "reason": reason,
    }
    if sqlite_db is None:
        _append(event, Path(path))
    else:
        try:
            append_local_record(sqlite_db, kind="memory", record_id=event["event_id"],
                                event_id=event["event_id"], created_at=event["created_at"], record=event)
        except LocalStoreError as exc:
            raise MemoryError(f"Archivage SQLite mémoire refusé: {exc}") from exc
    return True
