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


def _validate_event(event: Any, line_number: int) -> None:
    """Valide strictement la structure d'un événement avant toute utilisation."""
    if not isinstance(event, dict):
        raise MemoryError(f"Événement mémoire invalide ligne {line_number}.")
    event_type = event.get("event_type")
    if event_type == "remember":
        required = {
            "event_id", "event_type", "memory_id", "created_at", "actor",
            "category", "title", "content", "source", "confidence",
            "scope", "tags", "sensitivity",
        }
        if set(event) != required:
            raise MemoryError(f"Schéma remember invalide ligne {line_number}.")
        for field, limit in (("event_id", 36), ("memory_id", 36), ("actor", 120),
                             ("title", 120), ("content", 2000)):
            value = event[field]
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise MemoryError(f"Champ {field} invalide ligne {line_number}.")
        try:
            uuid.UUID(event["event_id"])
            uuid.UUID(event["memory_id"])
            datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
        except (ValueError, TypeError, AttributeError):
            raise MemoryError(f"Identifiant ou date invalide ligne {line_number}.")
        if (event["category"] not in CATEGORIES or event["scope"] not in SCOPES
                or event["sensitivity"] != "normal"):
            raise MemoryError(f"Métadonnées invalides ligne {line_number}.")
        confidence = event["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise MemoryError(f"Confiance invalide ligne {line_number}.")
        source = event["source"]
        if not isinstance(source, dict) or set(source) != {"type", "id"}:
            raise MemoryError(f"Source invalide ligne {line_number}.")
        for value in source.values():
            if not isinstance(value, str) or not value.strip() or len(value) > 120:
                raise MemoryError(f"Source invalide ligne {line_number}.")
        tags = event["tags"]
        if not isinstance(tags, list) or len(tags) > 10 or any(
            not isinstance(tag, str) or not tag.strip() or len(tag) > 30 for tag in tags
        ):
            raise MemoryError(f"Tags invalides ligne {line_number}.")
        _safe_tree(event["content"])
        if SECRET_PATTERN.search(event["actor"] + event["title"] + event["content"]):
            raise MemoryError(f"Contenu sensible ligne {line_number}.")
    elif event_type == "supersede":
        required = {"event_id", "event_type", "target_memory_id", "created_at", "actor", "reason"}
        if set(event) != required:
            raise MemoryError(f"Schéma supersede invalide ligne {line_number}.")
        for field, limit in (("event_id", 36), ("target_memory_id", 36),
                             ("actor", 120), ("reason", 240)):
            value = event[field]
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise MemoryError(f"Champ {field} invalide ligne {line_number}.")
        try:
            uuid.UUID(event["event_id"])
            uuid.UUID(event["target_memory_id"])
            datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
        except (ValueError, TypeError, AttributeError):
            raise MemoryError(f"Identifiant ou date invalide ligne {line_number}.")
        if SECRET_PATTERN.search(event["actor"] + event["reason"]):
            raise MemoryError(f"Contenu sensible ligne {line_number}.")
    else:
        raise MemoryError(f"Type d'événement invalide ligne {line_number}.")


def _read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events = []
    seen = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MemoryError(f"Journal mémoire corrompu ligne {number}.") from exc
        _validate_event(event, number)
        if event["event_id"] in seen:
            raise MemoryError(f"Événement mémoire dupliqué ligne {number}.")
        seen.add(event["event_id"])
        events.append(event)

    # Les événements de clôture doivent référencer une mémoire déjà créée.
    memory_ids = set()
    superseded_ids = set()
    for number, event in enumerate(events, 1):
        if event["event_type"] == "remember":
            memory_id = event["memory_id"]
            if memory_id in memory_ids:
                raise MemoryError(f"Identifiant mémoire dupliqué ligne {number}.")
            memory_ids.add(memory_id)
        else:
            target_id = event["target_memory_id"]
            if target_id not in memory_ids:
                raise MemoryError(f"Événement supersede orphelin ligne {number}.")
            if target_id in superseded_ids:
                raise MemoryError(f"Événement supersede dupliqué ligne {number}.")
            superseded_ids.add(target_id)
    return events


def _append(event: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)


def remember_fact(
    *, principal: object, category: str, title: str, content: str,
    source_type: str, source_id: str, confidence: float = 0.8,
    scope: str = "shared", tags: list[str] | None = None,
    sensitivity: str = "normal", path: Path = DEFAULT_PATH,
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
    _append(event, Path(path))
    return {key: value for key, value in event.items() if key != "event_type"}


def search_memory(
    *, principal: object, query: str = "", category: str | None = None,
    scope: str | None = None, limit: int = 20, path: Path = DEFAULT_PATH,
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
) -> bool:
    """Archive logiquement une entrée par événement ; l'historique reste intact."""
    memory_id = _safe_text(memory_id, "memory_id", 120)
    authenticated = require_authenticated_agent_principal(principal)
    actor = authenticated.agent_id
    reason = _safe_text(reason, "reason", 240)
    events = _read_events(Path(path))
    target = next((e for e in events if e["event_type"] == "remember" and e["memory_id"] == memory_id), None)
    if target is None:
        raise MemoryError("Entrée mémoire introuvable.")
    if target["category"] == "decision" or target["scope"] == "owner":
        raise MemoryError("Un agent ne peut pas archiver une mémoire réservée au propriétaire.")
    if target["scope"] == "agent" and actor != target["actor"]:
        raise MemoryError("Un agent ne peut pas archiver la mémoire privée d’un autre agent.")
    if any(e.get("target_memory_id") == memory_id for e in events if e["event_type"] == "supersede"):
        return False
    _append({
        "event_id": str(uuid.uuid4()), "event_type": "supersede",
        "target_memory_id": memory_id, "created_at": _timestamp(),
        "actor": actor, "reason": reason,
    }, Path(path))
    return True
