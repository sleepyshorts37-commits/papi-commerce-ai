"""Cartes d'identité professionnelles vérifiables pour les agents PAPI."""
from __future__ import annotations

from datetime import date
from typing import Any

CARD_SCHEMA_VERSION = 1
VALID_STATUSES = {"defined", "planned", "active", "suspended", "revoked"}
VALID_AUTONOMY_LEVELS = {"restricted", "bounded", "elevated"}
_ALLOWED_ID = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")


class IdentityCardError(ValueError):
    """Carte d'identité absente, incohérente ou invalide."""


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and all(char in _ALLOWED_ID for char in value)


def _valid_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def create_identity_card(agent: dict[str, Any], created_at: str,
                         manager_agent_id: str | None = None) -> dict[str, Any]:
    """Construit une carte stable à partir du profil du registre, sans activer l'agent."""
    if not isinstance(agent, dict):
        raise IdentityCardError("Profil agent invalide.")
    for field in ("id", "name", "role", "department", "status", "permissions"):
        if not isinstance(agent.get(field), str if field != "permissions" else list):
            raise IdentityCardError(f"Champ agent invalide ou absent : {field}.")
    agent_id = agent["id"]
    if not _valid_id(agent_id):
        raise IdentityCardError("Identifiant agent invalide.")
    if not _valid_date(created_at):
        raise IdentityCardError("La date doit être au format ISO YYYY-MM-DD.")
    if not isinstance(agent["status"], str) or agent["status"] not in VALID_STATUSES:
        raise IdentityCardError("Statut agent invalide.")
    if any(not isinstance(agent[field], str) or not agent[field].strip()
           for field in ("name", "role", "department")):
        raise IdentityCardError("Nom, fonction et service doivent être renseignés.")
    permissions = agent["permissions"]
    if any(not isinstance(item, str) or not item.strip() for item in permissions):
        raise IdentityCardError("Permissions agent invalides.")
    if len(set(permissions)) != len(permissions):
        raise IdentityCardError("Permissions agent dupliquées.")
    autonomy = agent.get("autonomy_level", "bounded")
    if not isinstance(autonomy, str) or autonomy not in VALID_AUTONOMY_LEVELS:
        raise IdentityCardError("Niveau d'autonomie invalide.")
    skills = agent.get("skills", [])
    if not isinstance(skills, list) or any(not isinstance(item, str) or not item.strip() for item in skills):
        raise IdentityCardError("Compétences agent invalides.")
    if len(set(skills)) != len(skills):
        raise IdentityCardError("Compétences agent dupliquées.")
    if manager_agent_id is not None and (not _valid_id(manager_agent_id) or manager_agent_id == agent_id):
        raise IdentityCardError("Responsable hiérarchique invalide.")
    mission = agent.get("mission", agent["role"])
    if not isinstance(mission, str) or not mission.strip():
        raise IdentityCardError("Mission agent invalide.")
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "employee_id": f"PAPI-AG-{agent_id.upper()}",
        "agent_id": agent_id,
        "name": agent["name"],
        "position": agent["role"],
        "department": agent["department"],
        "manager_agent_id": manager_agent_id,
        "mission": mission,
        "skills": list(skills),
        "autonomy_level": autonomy,
        "permissions": list(permissions),
        "status": agent["status"],
        "created_at": created_at,
        "employment_history": [],
    }


def validate_identity_card(card: dict[str, Any]) -> None:
    """Lève IdentityCardError si la carte ne respecte pas le schéma professionnel."""
    if not isinstance(card, dict) or card.get("schema_version") != CARD_SCHEMA_VERSION:
        raise IdentityCardError("Version ou structure de carte invalide.")
    required_text = ("agent_id", "name", "position", "department", "mission")
    if any(not isinstance(card.get(field), str) or not card[field].strip() for field in required_text):
        raise IdentityCardError("Identité professionnelle incomplète.")
    agent_id = card["agent_id"]
    if not _valid_id(agent_id):
        raise IdentityCardError("Identifiant agent invalide.")
    if card.get("employee_id") != f"PAPI-AG-{agent_id.upper()}":
        raise IdentityCardError("Identifiant employé incohérent.")
    manager = card.get("manager_agent_id")
    if manager is not None and (not _valid_id(manager) or manager == agent_id):
        raise IdentityCardError("Responsable hiérarchique invalide.")
    status = card.get("status")
    autonomy = card.get("autonomy_level")
    if (not isinstance(status, str) or status not in VALID_STATUSES
            or not isinstance(autonomy, str) or autonomy not in VALID_AUTONOMY_LEVELS):
        raise IdentityCardError("Statut ou autonomie invalide.")
    permissions = card.get("permissions")
    if not isinstance(permissions, list) or any(not isinstance(p, str) or not p.strip() for p in permissions):
        raise IdentityCardError("Permissions de carte invalides.")
    if len(set(permissions)) != len(permissions):
        raise IdentityCardError("Permissions de carte dupliquées.")
    skills = card.get("skills")
    if not isinstance(skills, list) or any(not isinstance(skill, str) or not skill.strip() for skill in skills):
        raise IdentityCardError("Compétences de carte invalides.")
    if len(set(skills)) != len(skills):
        raise IdentityCardError("Compétences de carte dupliquées.")
    if not _valid_date(card.get("created_at")):
        raise IdentityCardError("Date de création invalide.")
    history = card.get("employment_history")
    if not isinstance(history, list):
        raise IdentityCardError("Historique professionnel invalide.")
    for entry in history:
        if not isinstance(entry, dict) or set(entry) - {"role", "status", "date"}:
            raise IdentityCardError("Entrée d'historique invalide.")
        if (not isinstance(entry.get("role"), str) or not entry["role"].strip()
                or not isinstance(entry.get("status"), str)
                or entry["status"] not in VALID_STATUSES or not _valid_date(entry.get("date"))):
            raise IdentityCardError("Entrée d'historique invalide.")
