"""Mémoire structurée des agents : propositions, rappel contrôlé et projection en lecture seule."""
from __future__ import annotations

import re
from typing import Any

from .audit import validate_event
from .identity_security import validate_identity_registry

MEMORY_PERMISSION = "manage_own_memory"
ACTIVE = {"active", "deployed"}
CATEGORIES = {"experience", "decision", "knowledge", "lesson", "error"}
VISIBILITIES = {"private", "team", "company"}
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,119}$")
_EMAIL = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d .()/-]{7,}\d)(?!\w)")
_SENSITIVE = re.compile(r"\b(password|mot de passe|secret|token|api key|clé api|carte bancaire|cvv|otp|pin)\b", re.I)


class AgentMemoryError(ValueError):
    """Entrée mémoire invalide ou accès non autorisé."""


def _clean(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise AgentMemoryError(f"{field} doit contenir entre 1 et {maximum} caractères.")
    if _EMAIL.search(value) or _PHONE.search(value) or _SENSITIVE.search(value):
        raise AgentMemoryError(f"{field} contient potentiellement une donnée sensible.")
    return value.strip()


def _maps(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    validate_identity_registry(document)
    return {item["agent_id"]: item for item in document["identities"]}


def _authorized(agent_id: str, identities: dict[str, dict[str, Any]]) -> dict[str, Any]:
    identity = identities.get(agent_id)
    if identity is None or identity.get("status") not in ACTIVE or identity.get("profile_state") != "complete":
        raise AgentMemoryError("Agent inconnu, inactif ou profil incomplet.")
    if MEMORY_PERMISSION in identity.get("prohibited_actions", []) or MEMORY_PERMISSION not in identity.get("permissions", []):
        raise AgentMemoryError("Permission manage_own_memory absente ou interdite.")
    return identity


def build_memory_candidate(
    *, memory_id: str, agent_id: str, category: str, title: str,
    content: str, tags: list[str], source_ref: str | None,
    visibility: str, created_at: str,
    identity_document: dict[str, Any],
) -> dict[str, Any]:
    """Prépare une entrée pour la mémoire propre de l'agent ; ne l'enregistre pas."""
    identities = _maps(identity_document)
    _authorized(agent_id, identities)
    if not isinstance(memory_id, str) or not _ID.fullmatch(memory_id):
        raise AgentMemoryError("memory_id invalide.")
    if category not in CATEGORIES or visibility not in VISIBILITIES:
        raise AgentMemoryError("Catégorie ou visibilité invalide.")
    clean_title = _clean(title, "title", 160)
    clean_content = _clean(content, "content", 500)
    if not isinstance(tags, list) or len(tags) > 10 or any(not isinstance(tag, str) for tag in tags):
        raise AgentMemoryError("tags doit être une liste de 0 à 10 textes.")
    clean_tags = sorted({_clean(tag, "tag", 40).lower() for tag in tags})
    if source_ref is not None:
        source_ref = _clean(source_ref, "source_ref", 120)
    if not isinstance(created_at, str) or not created_at.strip() or len(created_at) > 40:
        raise AgentMemoryError("created_at invalide.")
    details = {
        "memory_id": memory_id, "category": category, "title": clean_title,
        "content": clean_content, "tags": clean_tags,
        "source_ref": source_ref, "visibility": visibility,
    }
    event = {
        "event_id": f"MEMORY-EVENT-{memory_id}", "occurred_at": created_at,
        "actor": agent_id, "action": "agent.memory.proposed",
        "entity_type": "agent_memory", "entity_id": memory_id,
        "details": details,
    }
    try:
        validate_event(event)
    except ValueError as exc:
        raise AgentMemoryError(str(exc)) from exc
    return {
        "status": "proposal_candidate", "agent_id": agent_id,
        "memory": {**details, "created_at": created_at},
        "permission_checked": MEMORY_PERMISSION,
        "scope_enforced": "own_agent_memory",
        "runtime_identity_authenticated": False,
        "persisted": False, "shared": False, "read_only": True,
    }


def build_memory_center(events: list[dict[str, Any]], identity_document: dict[str, Any]) -> dict[str, Any]:
    """Projette les seules entrées agent.memory.recorded présentes dans le journal."""
    identities = _maps(identity_document)
    seen: set[str] = set()
    entries: list[dict[str, Any]] = []
    rejected = 0
    required = {"memory_id", "category", "title", "content", "tags", "source_ref", "visibility"}
    for event in events:
        if not isinstance(event, dict) or event.get("action") != "agent.memory.recorded":
            continue
        try:
            validate_event(event)
            if event["entity_type"] != "agent_memory" or event["entity_id"] != event["details"].get("memory_id"):
                raise AgentMemoryError("Type ou identifiant mémoire incohérent.")
            d, agent_id = event["details"], event["actor"]
            if set(d) != required:
                raise AgentMemoryError("Schéma mémoire invalide.")
            memory_id = d["memory_id"]
            if not isinstance(memory_id, str) or not _ID.fullmatch(memory_id) or memory_id in seen:
                raise AgentMemoryError("Identifiant mémoire dupliqué ou invalide.")
            _authorized(agent_id, identities)
            if d["category"] not in CATEGORIES or d["visibility"] not in VISIBILITIES:
                raise AgentMemoryError("Catégorie ou visibilité invalide.")
            title, content = _clean(d["title"], "title", 160), _clean(d["content"], "content", 500)
            tags = d["tags"]
            if not isinstance(tags, list) or len(tags) > 10:
                raise AgentMemoryError("Tags invalides.")
            clean_tags = sorted({_clean(tag, "tag", 40).lower() for tag in tags})
            if d["source_ref"] is not None:
                _clean(d["source_ref"], "source_ref", 120)
            seen.add(memory_id)
            entries.append({
                "memory_id": memory_id, "agent_id": agent_id,
                "category": d["category"], "title": title, "content": content,
                "tags": clean_tags, "source_ref": d["source_ref"],
                "visibility": d["visibility"], "created_at": event["occurred_at"],
                "status": "recorded_memory",
            })
        except (ValueError, KeyError, TypeError):
            rejected += 1
    entries.sort(key=lambda item: (item["created_at"], item["memory_id"]))
    return {
        "status": "available" if entries else "no_recorded_memories",
        "entries": entries, "entry_count": len(entries),
        "rejected_events": rejected, "source": "explicit_append_only_audit_events",
        "read_only": True,
    }


def recall_agent_memory(
    *, agent_id: str, query: str, memory_center: dict[str, Any],
    identity_document: dict[str, Any],
) -> dict[str, Any]:
    """Recherche lexicale limitée aux mémoires privées de l'agent demandeur."""
    identities = _maps(identity_document)
    _authorized(agent_id, identities)
    terms = set(re.findall(r"[a-z0-9À-ÿ]{2,}", _clean(query, "query", 200).lower()))
    if not isinstance(memory_center, dict) or not isinstance(memory_center.get("entries"), list):
        raise AgentMemoryError("Centre mémoire invalide.")
    matches = []
    for entry in memory_center["entries"]:
        if not isinstance(entry, dict) or entry.get("agent_id") != agent_id:
            continue
        if entry.get("visibility") != "private":
            continue
        corpus = " ".join([str(entry.get("title", "")), str(entry.get("content", "")),
                           " ".join(entry.get("tags", []))]).lower()
        score = len(terms.intersection(re.findall(r"[a-z0-9À-ÿ]{2,}", corpus)))
        if score:
            matches.append((score, entry))
    matches.sort(key=lambda pair: (-pair[0], pair[1].get("created_at", ""), pair[1].get("memory_id", "")))
    return {
        "agent_id": agent_id, "query_terms": sorted(terms),
        "results": [{"score": score, **entry} for score, entry in matches[:10]],
        "result_count": min(len(matches), 10),
        "retrieval_method": "local_lexical_match",
        "cross_agent_access": False, "read_only": True,
    }
