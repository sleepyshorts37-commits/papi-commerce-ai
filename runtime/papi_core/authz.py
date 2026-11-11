"""Contrôle d'accès local des agents (sans authentification cryptographique).

La présence d'un identifiant d'agent ne prouve pas l'identité du processus appelant.
Ce module applique uniquement les permissions déclarées et refuse les agents non actifs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .registry import RegistryError, load_agents

ROOT = Path(__file__).resolve().parents[2]
AGENTS_FILE = ROOT / "data" / "agents.json"
OWNER_ONLY = {"spend_money", "withdraw_funds", "transfer_funds", "accept_legal_commitments",
              "grant_sensitive_access", "create_account", "subscribe_service", "buy_api_credits"}
EXTERNAL = {"send_email", "send_message", "publish_content", "contact_prospect"}
FINANCIAL = {"spend_money", "withdraw_funds", "transfer_funds", "issue_refund", "make_payment"}
LEGAL = {"accept_legal_commitments", "sign_contract", "accept_contract"}


class AccessDenied(PermissionError):
    """Accès refusé par la politique locale."""


def authorize_agent(agent_id: str, permission: str, agents_path: Path = AGENTS_FILE,
                    policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Autorise une capacité déclarée pour un agent dont le statut est explicitement active."""
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise AccessDenied("Identifiant d'agent obligatoire.")
    if not isinstance(permission, str) or not permission.strip():
        raise AccessDenied("Permission obligatoire.")
    try:
        agents = load_agents(agents_path)
    except RegistryError as exc:
        raise AccessDenied("Registre agents invalide : accès fermé.") from exc
    agent = agents.get(agent_id)
    if agent is None:
        raise AccessDenied("Agent inconnu.")
    if agent.get("status") != "active":
        raise AccessDenied("Agent non actif : statut défini/planifié insuffisant.")
    permissions = agent.get("permissions")
    prohibited = agent.get("prohibited")
    if not isinstance(permissions, list) or permission not in permissions:
        raise AccessDenied("Permission absente du profil agent.")
    if isinstance(prohibited, list) and permission in prohibited:
        raise AccessDenied("Action explicitement interdite pour cet agent.")
    if permission in OWNER_ONLY:
        raise AccessDenied("Action réservée au propriétaire ; aucun agent ne peut l'exécuter.")
    if policy is not None:
        if permission in EXTERNAL and policy.get("external_actions_enabled") is not True:
            raise AccessDenied("Actions externes désactivées par la politique.")
        if permission in FINANCIAL:
            permissions_policy = policy.get("action_permissions", {})
            financial = permissions_policy.get("financial", {}) if isinstance(permissions_policy, dict) else {}
            if not isinstance(financial, dict) or financial.get("enabled") is not True:
                raise AccessDenied("Actions financières désactivées par la politique.")
        if permission in LEGAL:
            permissions_policy = policy.get("action_permissions", {})
            legal = permissions_policy.get("legal", {}) if isinstance(permissions_policy, dict) else {}
            if not isinstance(legal, dict) or legal.get("enabled") is not True:
                raise AccessDenied("Actions juridiques désactivées par la politique.")
    return {"authorized": True, "agent_id": agent_id, "permission": permission,
            "mode": "local_policy_check", "identity_authenticated": False}
