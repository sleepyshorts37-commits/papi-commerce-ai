"""Contrôles d'identité documentaire et d'autorisation fail-closed."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any


class IdentitySecurityError(ValueError):
    """Identité ou demande d'autorisation invalide."""


_REQUIRED = {
    "identity_id", "agent_id", "full_name", "role", "department",
    "manager_id", "mission", "competencies", "objectives",
    "autonomy_level", "permissions", "prohibited_actions",
    "status", "created_at", "assignment_history", "evaluation_history",
    "profile_state",
}
_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{2,79}$")
_ACTIVE = {"active", "deployed"}


def validate_identity_registry(document: dict[str, Any]) -> dict[str, Any]:
    """Valide les identifiants uniques et les champs de chaque fiche."""
    if not isinstance(document, dict) or not isinstance(document.get("identities"), list):
        raise IdentitySecurityError("Le registre doit contenir une liste identities.")
    seen_ids: set[str] = set()
    seen_agents: set[str] = set()
    for index, item in enumerate(document["identities"]):
        if not isinstance(item, dict):
            raise IdentitySecurityError(f"Identité #{index + 1} invalide.")
        missing = _REQUIRED - item.keys()
        if missing:
            raise IdentitySecurityError(f"Identité #{index + 1}, champs absents : {', '.join(sorted(missing))}.")
        identity_id, agent_id = item["identity_id"], item["agent_id"]
        if not isinstance(identity_id, str) or not _ID_PATTERN.fullmatch(identity_id):
            raise IdentitySecurityError(f"Format identity_id invalide à l'entrée #{index + 1}.")
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise IdentitySecurityError(f"agent_id invalide à l'entrée #{index + 1}.")
        if identity_id in seen_ids or agent_id in seen_agents:
            raise IdentitySecurityError("Identifiant d'identité ou agent_id dupliqué.")
        seen_ids.add(identity_id)
        seen_agents.add(agent_id)
        for field in ("competencies", "objectives", "permissions", "prohibited_actions",
                      "assignment_history", "evaluation_history"):
            if not isinstance(item[field], list) or any(not isinstance(v, str) for v in item[field]):
                raise IdentitySecurityError(f"{field} doit être une liste de textes.")
        if item["manager_id"] is not None and not isinstance(item["manager_id"], str):
            raise IdentitySecurityError("manager_id doit être un texte ou null.")
        if item["status"] not in {"planned", "defined", "active", "suspended", "revoked", "deployed"}:
            raise IdentitySecurityError("Statut d'identité inconnu.")
        if item["profile_state"] not in {"incomplete", "complete"}:
            raise IdentitySecurityError("profile_state invalide.")
    return {
        "valid": True,
        "identities_count": len(document["identities"]),
        "unique_identity_ids": len(seen_ids),
        "unique_agent_ids": len(seen_agents),
        "read_only": True,
    }


def identity_fingerprint(identity: dict[str, Any]) -> str:
    """Empreinte SHA-256 déterministe ; ce n'est ni une signature ni une preuve d'auteur."""
    if not isinstance(identity, dict):
        raise IdentitySecurityError("identity doit être un objet.")
    payload = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_identity(
    identity: dict[str, Any], *, expected_fingerprint: str,
) -> dict[str, Any]:
    """Compare une empreinte attendue ; la provenance de cette empreinte doit être sécurisée ailleurs."""
    if not isinstance(expected_fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_fingerprint):
        raise IdentitySecurityError("Empreinte attendue invalide.")
    actual = identity_fingerprint(identity)
    return {
        "integrity_match": actual == expected_fingerprint,
        "fingerprint": actual,
        "verification_type": "sha256_integrity_comparison",
        "cryptographic_identity_authentication": False,
        "read_only": True,
    }


def authorize_agent_action(
    identity: dict[str, Any],
    *,
    registry_agent: dict[str, Any],
    requested_permission: str,
    expected_fingerprint: str,
) -> dict[str, Any]:
    """Autorise seulement les permissions explicitement listées ; refuse par défaut."""
    if not isinstance(identity, dict) or not isinstance(registry_agent, dict):
        raise IdentitySecurityError("Identité et fiche registre doivent être des objets.")
    if not isinstance(requested_permission, str) or not requested_permission.strip():
        raise IdentitySecurityError("Permission demandée invalide.")
    verification = verify_identity(identity, expected_fingerprint=expected_fingerprint)
    reasons: list[str] = []
    if not verification["integrity_match"]:
        reasons.append("identity_fingerprint_mismatch")
    if identity.get("agent_id") != registry_agent.get("id"):
        reasons.append("agent_registry_mismatch")
    if identity.get("identity_id") is None:
        reasons.append("identity_id_missing")
    if identity.get("status") not in _ACTIVE or registry_agent.get("status") not in _ACTIVE:
        reasons.append("agent_not_active")
    if identity.get("profile_state") != "complete":
        reasons.append("identity_profile_incomplete")
    if requested_permission in identity.get("prohibited_actions", []):
        reasons.append("action_explicitly_prohibited")
    if requested_permission not in identity.get("permissions", []):
        reasons.append("permission_not_granted")
    return {
        "decision": "deny" if reasons else "allow",
        "agent_id": identity.get("agent_id"),
        "requested_permission": requested_permission,
        "reasons": reasons,
        "identity_integrity_match": verification["integrity_match"],
        "owner_approval_checked": False,
        "runtime_identity_authenticated": False,
        "action_executed": False,
        "read_only": True,
    }
