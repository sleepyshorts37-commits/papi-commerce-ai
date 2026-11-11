"""Préparation contrôlée de l'intégration de nouveaux agents PAPI."""
from __future__ import annotations

from datetime import date
from typing import Any

from .agent_identity_card import create_identity_card, validate_identity_card
from .registry import RegistryError, load_agents


class OnboardingError(ValueError):
    """Demande d'intégration d'un agent invalide."""


def prepare_agent_onboarding(*, agent_id: str, name: str, role: str,
                             department: str, mission: str,
                             manager_agent_id: str, created_at: str,
                             agents_path=None, skills: list[str] | None = None,
                             permissions: list[str] | None = None,
                             autonomy_level: str = "bounded") -> dict[str, Any]:
    """Prépare un dossier candidat et sa carte, sans l'ajouter au registre ni l'activer."""
    from .registry import AGENTS_FILE

    if not all(isinstance(value, str) and value.strip() for value in
               (agent_id, name, role, department, mission, manager_agent_id)):
        raise OnboardingError("Identité, poste, mission et responsable obligatoires.")
    if not isinstance(created_at, str):
        raise OnboardingError("Date de création invalide.")
    try:
        date.fromisoformat(created_at)
    except ValueError as exc:
        raise OnboardingError("Date au format ISO YYYY-MM-DD obligatoire.") from exc
    try:
        existing = load_agents(agents_path or AGENTS_FILE)
    except RegistryError as exc:
        raise OnboardingError("Registre agents invalide : intégration refusée.") from exc
    if agent_id in existing:
        raise OnboardingError("Identifiant déjà utilisé.")
    manager = existing.get(manager_agent_id)
    if manager is None or manager.get("status") in {"suspended", "revoked"}:
        raise OnboardingError("Responsable inconnu ou indisponible.")
    if manager_agent_id == agent_id:
        raise OnboardingError("Un agent ne peut pas être son propre responsable.")
    if not isinstance(skills or [], list) or any(not isinstance(item, str) or not item.strip() for item in (skills or [])):
        raise OnboardingError("Liste de compétences invalide.")
    if not isinstance(permissions or [], list) or any(not isinstance(item, str) or not item.strip() for item in (permissions or [])):
        raise OnboardingError("Liste de permissions invalide.")
    if len(set(permissions or [])) != len(permissions or []):
        raise OnboardingError("Permissions dupliquées.")
    profile = {
        "id": agent_id,
        "name": name.strip(),
        "role": role.strip(),
        "department": department.strip(),
        "mission": mission.strip(),
        "manager_agent_id": manager_agent_id,
        "status": "planned",
        "permissions": list(permissions or []),
        "prohibited": [],
        "skills": list(skills or []),
        "autonomy_level": autonomy_level,
    }
    try:
        card = create_identity_card(profile, created_at, manager_agent_id)
        validate_identity_card(card)
    except ValueError as exc:
        raise OnboardingError(str(exc)) from exc
    return {
        "onboarding_status": "prepared",
        "activation_status": "not_activated",
        "profile": profile,
        "identity_card": card,
        "requires_owner_approval_for_sensitive_actions": True,
    }
