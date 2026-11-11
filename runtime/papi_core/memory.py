"""Mémoire partagée locale, traçable et append-only pour PAPI."""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
        if not isinstance(event, dict) or event.get("event_id") in seen:
            raise MemoryError(f"Événement mémoire invalide ou dupliqué ligne {number}.")
        if event.get("event_type") not in {"remember", "supersede"}:
            raise MemoryError(f"Type d'événement invalide ligne {number}.")
        seen.add(event["event_id"])
        events.append(event)
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
    *, actor: str, category: str, title: str, content: str,
    source_type: str, source_id: str, confidence: float = 0.8,
    scope: str = "shared", tags: list[str] | None = None,
    sensitivity: str = "normal", path: Path = DEFAULT_PATH,
) -> dict[str, Any]:
    """Ajoute un fait traçable ; ne modifie jamais une entrée existante."""
    actor = _safe_text(actor, "actor", 120)
    title = _safe_text(title, "title", 120)
    content = _safe_text(content, "content", 2000)
    source_type = _safe_text(source_type, "source_type", 40)
    source_id = _safe_text(source_id, "source_id", 120)
    if category not in CATEGORIES or scope not in SCOPES or sensitivity not in SENSITIVITIES:
        raise MemoryError("Catégorie, portée ou sensibilité invalide.")
    if category == "decision" and actor != "owner":
        raise MemoryError("Seul le propriétaire peut enregistrer une décision officielle.")
    if scope == "owner" and actor != "owner":
        raise MemoryError("La mémoire owner est réservée au propriétaire.")
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
    *, query: str = "", actor: str = "owner", category: str | None = None,
    scope: str | None = None, limit: int = 20, path: Path = DEFAULT_PATH,
) -> list[dict[str, Any]]:
    """Recherche locale ; les entrées privées ne sont visibles que dans leur portée."""
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
        if event["scope"] == "owner" and actor != "owner":
            continue
        if event["scope"] == "agent" and actor not in {"owner", event["actor"]}:
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
    *, memory_id: str, actor: str, reason: str, path: Path = DEFAULT_PATH,
) -> bool:
    """Archive logiquement une entrée par événement ; l'historique reste intact."""
    memory_id = _safe_text(memory_id, "memory_id", 120)
    actor = _safe_text(actor, "actor", 120)
    reason = _safe_text(reason, "reason", 240)
    events = _read_events(Path(path))
    target = next((e for e in events if e["event_type"] == "remember" and e["memory_id"] == memory_id), None)
    if target is None:
        raise MemoryError("Entrée mémoire introuvable.")
    if target["category"] == "decision" and actor != "owner":
        raise MemoryError("Seul le propriétaire peut archiver une décision officielle.")
    if target["scope"] == "owner" and actor != "owner":
        raise MemoryError("Seul le propriétaire peut archiver cette entrée.")
    if any(e.get("target_memory_id") == memory_id for e in events if e["event_type"] == "supersede"):
        return False
    _append({
        "event_id": str(uuid.uuid4()), "event_type": "supersede",
        "target_memory_id": memory_id, "created_at": _timestamp(),
        "actor": actor, "reason": reason,
    }, Path(path))
    return True
