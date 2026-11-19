"""Validation documentaire des profils et de la délégation hiérarchique.

Ce registre décrit les profils ; il ne remplace jamais l'authentification
cryptographique ni la politique d'autorisation d'exécution.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_PROFILES_FILE = Path(__file__).resolve().parents[2] / "data" / "agent_profiles.json"
VALID_STATUSES = {"planned", "defined", "active", "suspended", "revoked", "retired"}
VALID_AUTONOMY = {"manual_only", "proposal_only", "supervised", "bounded"}
REQUIRED_FIELDS = {
    "id", "name", "role", "team", "manager_id", "mission", "skills",
    "objectives", "autonomy_level", "permissions", "status", "history",
}


class AgentProfileError(ValueError):
    """Profil d'agent ou délégation incohérents."""


def load_agent_profiles(path: Path = DEFAULT_PROFILES_FILE) -> dict[str, dict[str, Any]]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AgentProfileError("Registre de profils absent, illisible ou invalide.") from exc
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise AgentProfileError("Version du registre de profils non prise en charge.")
    records = document.get("profiles")
    if not isinstance(records, list):
        raise AgentProfileError("'profiles' doit être une liste.")
    profiles: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("id"), str) or not record["id"]:
            raise AgentProfileError("Chaque profil doit posséder un identifiant texte.")
        if record["id"] in profiles:
            raise AgentProfileError(f"Profil dupliqué : {record['id']}.")
        profiles[record["id"]] = record
    return profiles


def _strings(value: Any, field: str, *, allow_empty: bool = False) -> set[str]:
    if not isinstance(value, list):
        raise AgentProfileError(f"{field} doit être une liste.")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise AgentProfileError(f"{field} ne doit contenir que des textes non vides.")
    if len(value) != len(set(value)):
        raise AgentProfileError(f"{field} contient des doublons.")
    if not allow_empty and not value:
        raise AgentProfileError(f"{field} ne peut pas être vide.")
    return set(value)


def validate_agent_profiles(
    profiles: dict[str, dict[str, Any]],
    agents: dict[str, dict[str, Any]],
) -> list[str]:
    """Valide les profils, les références de manager et les droits délégués."""
    errors: list[str] = []
    if not isinstance(profiles, dict) or not isinstance(agents, dict):
        return ["Les registres de profils et d'agents doivent être des objets."]

    parsed: dict[str, tuple[dict[str, Any], set[str], set[str]]] = {}
    for profile_id, profile in profiles.items():
        try:
            if not isinstance(profile, dict) or profile.get("id") != profile_id:
                raise AgentProfileError("Clé et identifiant de profil incohérents.")
            missing = REQUIRED_FIELDS - profile.keys()
            if missing:
                raise AgentProfileError("Champs absents : " + ", ".join(sorted(missing)))
            if profile_id not in agents:
                raise AgentProfileError("Agent absent du registre central.")
            source = agents[profile_id]
            for field in ("name", "role", "team", "mission"):
                value = profile.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise AgentProfileError(f"{field} doit être un texte non vide.")
            if profile["name"] != source.get("name") or profile["role"] != source.get("role"):
                raise AgentProfileError("Le nom et la fonction doivent correspondre au registre central.")
            if profile["team"] != source.get("department"):
                raise AgentProfileError("L'équipe doit correspondre au département déclaré.")
            if profile["status"] not in VALID_STATUSES:
                raise AgentProfileError("Statut de profil inconnu.")
            if profile["autonomy_level"] not in VALID_AUTONOMY:
                raise AgentProfileError("Niveau d'autonomie inconnu.")
            if profile["status"] == "active" and source.get("status") != "active":
                raise AgentProfileError("Un profil ne peut pas activer seul un agent non actif dans le registre central.")
            if profile["manager_id"] is not None and (
                not isinstance(profile["manager_id"], str) or not profile["manager_id"].strip()
            ):
                raise AgentProfileError("manager_id doit être un identifiant ou null.")
            if profile["manager_id"] == profile_id:
                raise AgentProfileError("Un agent ne peut pas être son propre responsable.")
            _strings(profile["skills"], "skills")
            _strings(profile["objectives"], "objectives")
            permissions = _strings(profile["permissions"], "permissions", allow_empty=True)
            delegable = _strings(profile.get("delegable_permissions", []), "delegable_permissions", allow_empty=True)
            if not delegable.issubset(permissions):
                raise AgentProfileError("Un agent ne peut déléguer que ses propres permissions déclarées.")
            history = profile["history"]
            if not isinstance(history, list):
                raise AgentProfileError("history doit être une liste.")
            for event in history:
                if not isinstance(event, dict) or not all(
                    isinstance(event.get(key), str) and event[key].strip()
                    for key in ("at", "action", "actor")
                ):
                    raise AgentProfileError("Chaque événement d'historique exige at, action et actor.")
                try:
                    parsed_at = datetime.fromisoformat(event["at"].replace("Z", "+00:00"))
                except ValueError as exc:
                    raise AgentProfileError("Horodatage d'historique invalide.") from exc
                if parsed_at.tzinfo is None or parsed_at.utcoffset() is None:
                    raise AgentProfileError("L'historique doit inclure un fuseau horaire.")
            parsed[profile_id] = (profile, permissions, delegable)
        except AgentProfileError as exc:
            errors.append(f"Profil {profile_id}: {exc}")

    for profile_id, (profile, permissions, _) in parsed.items():
        manager_id = profile.get("manager_id")
        if manager_id is None:
            continue
        manager = parsed.get(manager_id)
        if manager is None:
            errors.append(f"Profil {profile_id}: responsable inconnu ou sans profil complet.")
            continue
        if not permissions.issubset(manager[2]):
            errors.append(f"Profil {profile_id}: permissions non déléguées par {manager_id}.")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(profile_id: str) -> None:
        if profile_id in visiting:
            errors.append(f"Hiérarchie cyclique détectée à {profile_id}.")
            return
        if profile_id in visited:
            return
        visiting.add(profile_id)
        profile = profiles.get(profile_id, {})
        manager_id = profile.get("manager_id") if isinstance(profile, dict) else None
        if isinstance(manager_id, str) and manager_id in profiles:
            visit(manager_id)
        visiting.discard(profile_id)
        visited.add(profile_id)

    for profile_id in profiles:
        visit(profile_id)
    return errors


def resolve_effective_permissions(
    agent_id: str, profiles: dict[str, dict[str, Any]]
) -> set[str]:
    """Retourne l'intersection des permissions explicitement déléguées par la hiérarchie."""
    if agent_id not in profiles:
        raise AgentProfileError("Profil inconnu.")
    current = profiles[agent_id]
    if current.get("status") != "active":
        return set()
    effective = set(current.get("permissions", []))
    seen = {agent_id}
    manager_id = current.get("manager_id")
    while manager_id is not None:
        if manager_id in seen or manager_id not in profiles:
            raise AgentProfileError("Hiérarchie invalide.")
        seen.add(manager_id)
        manager = profiles[manager_id]
        if manager.get("status") != "active":
            return set()
        effective.intersection_update(manager.get("delegable_permissions", []))
        manager_id = manager.get("manager_id")
    return effective
