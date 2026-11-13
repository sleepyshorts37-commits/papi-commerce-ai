"""Cartes d'identité professionnelles vérifiables pour les agents PAPI."""
from __future__ import annotations

from datetime import date
from typing import Any

CARD_SCHEMA_VERSION = 1
VALID_STATUSES = {"defined", "planned", "active", "suspended", "revoked"}
VALID_AUTONOMY_LEVELS = {"restricted", "bounded", "elevated"}


class IdentityCardError(ValueError):
    """Carte d'identité absente, incohérente ou invalide."""


def create_identity_card(agent: dict[str, Any], created_at: str,
                         manager_agent_id: str | None = None) -> dict[str, Any]:
    """Construit une carte stable à partir du profil du registre, sans activer l'agent."""
    if not isinstance(agent, dict):
        raise IdentityCardError("Profil agent invalide.")
    for field in ("id", "name", "role", "department", "status", "permissions"):
        if not isinstance(agent.get(field), str if field != "permissions" else list):
            raise IdentityCardError(f"Champ agent invalide ou absent : {field}.")
    agent_id = agent["id"]
    if not agent_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in agent_id):
        raise IdentityCardError("Identifiant agent invalide.")
    if not isinstance(created_at, str):
        raise IdentityCardError("Date de création invalide.")
    try:
        date.fromisoformat(created_at)
    except ValueError as exc:
        raise IdentityCardError("La date doit être au format ISO YYYY-MM-DD.") from exc
    if agent["status"] not in VALID_STATUSES:
        raise IdentityCardError("Statut agent invalide.")
    permissions = agent["permissions"]
    if any(not isinstance(item, str) or not item for item in permissions):
        raise IdentityCardError("Permissions agent invalides.")
    if len(set(permissions)) != len(permissions):
        raise IdentityCardError("Permissions agent dupliquées.")
    autonomy = agent.get("autonomy_level", "bounded")
    if autonomy not in VALID_AUTONOMY_LEVELS:
        raise IdentityCardError("Niveau d'autonomie invalide.")
    skills = agent.get("skills", [])
    if not isinstance(skills, list) or any(not isinstance(item, str) or not item for item in skills):
        raise IdentityCardError("Compétences agent invalides.")
    if manager_agent_id is not None and (not isinstance(manager_agent_id, str) or not manager_agent_id):
        raise IdentityCardError("Responsable hiérarchique invalide.")
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "employee_id": f"PAPI-AG-{agent_id.upper()}",
        "agent_id": agent_id,
        "name": agent["name"],
        "position": agent["role"],
        "department": agent["department"],
        "manager_agent_id": manager_agent_id,
        "mission": agent.get("mission", agent["role"]),
        "skills": list(skills),
        "autonomy_level": autonomy,
        "permissions": list(permissions),
        "status": agent["status"],
        "created_at": created_at,
        "employment_history": [],
    }


def validate_identity_card(card: dict[str, Any]) -> None:
    """Lève IdentityCardError si la carte ne respecte pas le schéma minimal."""
    if not isinstance(card, dict) or card.get("schema_version") != CARD_SCHEMA_VERSION:
        raise IdentityCardError("Version ou structure de carte invalide.")
    required_text = (
        "employee_id", "agent_id", "name", "position", "department", "mission", "created_at",
    )
    if any(not isinstance(card.get(field), str) or not card[field].strip()
           for field in required_text):
        raise IdentityCardError("Identité professionnelle incomplète.")
    agent_id = card["agent_id"]
    if any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
           for char in agent_id):
        raise IdentityCardError("Identifiant agent invalide.")
    if card["employee_id"] != f"PAPI-AG-{agent_id.upper()}":
        raise IdentityCardError("Identifiant employé incohérent.")
    if card.get("manager_agent_id") is not None:
        manager_id = card["manager_agent_id"]
        if not isinstance(manager_id, str) or not manager_id.strip():
            raise IdentityCardError("Responsable hiérarchique invalide.")
    if not isinstance(card.get("status"), str) or card["status"] not in VALID_STATUSES:
        raise IdentityCardError("Statut agent invalide.")
    if not isinstance(card.get("autonomy_level"), str) or card["autonomy_level"] not in VALID_AUTONOMY_LEVELS:
        raise IdentityCardError("Niveau d'autonomie invalide.")
    permissions = card.get("permissions")
    if not isinstance(permissions, list) or any(
        not isinstance(permission, str) or not permission.strip()
        for permission in permissions
    ):
        raise IdentityCardError("Permissions de carte invalides.")
    if len(set(permissions)) != len(permissions):
        raise IdentityCardError("Permissions de carte dupliquées.")
    skills = card.get("skills", [])
    if not isinstance(skills, list) or any(
        not isinstance(skill, str) or not skill.strip() for skill in skills
    ):
        raise IdentityCardError("Compétences de carte invalides.")
    if not isinstance(card.get("employment_history"), list):
        raise IdentityCardError("Historique professionnel invalide.")
    try:
        date.fromisoformat(card["created_at"])
    except (TypeError, ValueError) as exc:
        raise IdentityCardError("Date de création invalide.") from exc
