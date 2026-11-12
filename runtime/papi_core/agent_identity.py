"""Validation des cartes d'identité professionnelles PAPI (registre documentaire)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

VALID_AUTONOMY = {"none", "assisted", "bounded", "supervised"}
VALID_STATUSES = {"planned", "active", "suspended", "revoked"}
REQUIRED_FIELDS = {
    "identity_id", "agent_id", "full_name", "role", "department",
    "manager_id", "mission", "competencies", "objectives",
    "autonomy_level", "permissions", "prohibited_actions", "status",
    "created_at", "assignment_history", "evaluation_history", "profile_state",
}


class AgentIdentityError(ValueError):
    """Carte d'identité professionnelle invalide."""


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_identity(card: dict[str, Any], agents: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if not isinstance(card, dict):
        return ["La carte doit être un objet."]
    missing = sorted(REQUIRED_FIELDS - card.keys())
    if missing:
        return [f"Champs obligatoires absents : {', '.join(missing)}."]
    for field in ("identity_id", "agent_id", "full_name", "role", "department", "mission"):
        if not _nonempty_string(card.get(field)):
            errors.append(f"{field} doit être une chaîne non vide.")
    agent_id = card.get("agent_id")
    if _nonempty_string(agent_id) and agent_id not in agents:
        errors.append("agent_id ne correspond à aucun agent du registre.")
    if card.get("autonomy_level") not in VALID_AUTONOMY:
        errors.append("autonomy_level invalide.")
    if card.get("status") not in VALID_STATUSES:
        errors.append("status invalide.")
    if card.get("profile_state") not in {"incomplete", "complete"}:
        errors.append("profile_state doit être incomplete ou complete.")
    for field in ("competencies", "objectives", "permissions", "prohibited_actions",
                  "assignment_history", "evaluation_history"):
        value = card.get(field)
        if not isinstance(value, list):
            errors.append(f"{field} doit être une liste.")
        elif field in {"competencies", "objectives", "permissions", "prohibited_actions"}:
            if any(not _nonempty_string(item) for item in value):
                errors.append(f"{field} ne peut contenir que des chaînes non vides.")
            if len(value) != len(set(value)):
                errors.append(f"{field} contient des doublons.")
    created_at = card.get("created_at")
    if not _nonempty_string(created_at):
        errors.append("created_at doit être une date ISO 8601 avec fuseau.")
    else:
        try:
            parsed = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                errors.append("created_at doit inclure un fuseau horaire.")
        except ValueError:
            errors.append("created_at n'est pas une date ISO 8601 valide.")
    if card.get("status") == "active":
        if card.get("profile_state") != "complete":
            errors.append("Une carte incomplète ne peut pas être active.")
        if not _nonempty_string(card.get("manager_id")):
            errors.append("Un agent actif doit avoir un responsable hiérarchique.")
        if not card.get("competencies") or not card.get("objectives"):
            errors.append("Un agent actif doit avoir compétences et objectifs définis.")
    for field in ("assignment_history", "evaluation_history"):
        for index, entry in enumerate(card.get(field, []) if isinstance(card.get(field), list) else []):
            if not isinstance(entry, dict):
                errors.append(f"{field}[{index}] doit être un objet.")
    return errors


def validate_identity_registry(
    registry: dict[str, Any], agents: dict[str, dict[str, Any]]
) -> list[str]:
    if not isinstance(registry, dict) or registry.get("schema_version") != 1:
        raise AgentIdentityError("Registre d'identités invalide : schema_version 1 requis.")
    cards = registry.get("identities")
    if not isinstance(cards, list):
        raise AgentIdentityError("'identities' doit être une liste.")
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_agents: set[str] = set()
    for index, card in enumerate(cards):
        for error in validate_identity(card, agents):
            errors.append(f"Carte #{index + 1}: {error}")
        if isinstance(card, dict):
            identity_id = card.get("identity_id")
            agent_id = card.get("agent_id")
            if _nonempty_string(identity_id):
                if identity_id in seen_ids:
                    errors.append(f"Identifiant numérique dupliqué : {identity_id}.")
                seen_ids.add(identity_id)
            if _nonempty_string(agent_id):
                if agent_id in seen_agents:
                    errors.append(f"Une seule carte est autorisée par agent : {agent_id}.")
                seen_agents.add(agent_id)
    return errors
