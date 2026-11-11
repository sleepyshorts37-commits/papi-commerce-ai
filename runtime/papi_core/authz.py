"""Contrôle d'accès et authentification cryptographique des agents."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .identity import IdentityError, verify_request
from .identity_ed25519 import Ed25519IdentityError, verify_ed25519_request, DEFAULT_PUBLIC_REGISTRY
from .registry import RegistryError, load_agents

ROOT = Path(__file__).resolve().parents[2]
AGENTS_FILE = ROOT / "data" / "agents.json"
POLICY_FILE = ROOT / "config" / "policy.json"
OWNER_ONLY = {"spend_money", "withdraw_funds", "transfer_funds", "accept_legal_commitments",
              "grant_sensitive_access", "create_account", "subscribe_service", "buy_api_credits"}
EXTERNAL = {"send_email", "send_message", "publish_content", "contact_prospect"}
FINANCIAL = {"spend_money", "withdraw_funds", "transfer_funds", "issue_refund", "make_payment"}
LEGAL = {"accept_legal_commitments", "sign_contract", "accept_contract"}


class AccessDenied(PermissionError):
    """Accès refusé par la politique locale."""


def load_policy(path: Path = POLICY_FILE) -> dict[str, Any]:
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AccessDenied("Politique globale absente ou invalide : accès fermé.") from exc
    if not isinstance(policy, dict):
        raise AccessDenied("Politique globale invalide : accès fermé.")
    return policy


def authorize_agent(agent_id: str, permission: str, agents_path: Path = AGENTS_FILE,
                    policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Vérifie les permissions déclarées. Ne prouve pas l'identité du processus."""
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
        raise AccessDenied("Action réservée au propriétaire.")
    active_policy = policy if policy is not None else load_policy()
    if permission in EXTERNAL and active_policy.get("external_actions_enabled") is not True:
        raise AccessDenied("Actions externes désactivées par la politique.")
    if permission in FINANCIAL:
        permissions_policy = active_policy.get("action_permissions", {})
        financial = permissions_policy.get("financial", {}) if isinstance(permissions_policy, dict) else {}
        if not isinstance(financial, dict) or financial.get("enabled") is not True:
            raise AccessDenied("Actions financières désactivées par la politique.")
    if permission in LEGAL:
        permissions_policy = active_policy.get("action_permissions", {})
        legal = permissions_policy.get("legal", {}) if isinstance(permissions_policy, dict) else {}
        if not isinstance(legal, dict) or legal.get("enabled") is not True:
            raise AccessDenied("Actions juridiques désactivées par la politique.")
    return {"authorized": True, "agent_id": agent_id, "permission": permission,
            "mode": "local_policy_check", "identity_authenticated": False}


def authorize_authenticated_agent(agent_id: str, permission: str, envelope: dict[str, Any],
                                  *, task_id: str, handler: str,
                                  agents_path: Path = AGENTS_FILE,
                                  policy: dict[str, Any] | None = None,
                                  key_dir: Path | None = None,
                                  replay_db: Path | None = None,
                                  public_registry: Path = DEFAULT_PUBLIC_REGISTRY,
                                  shared_identity_verifier: Any | None = None) -> dict[str, Any]:
    """Vérifie signature, liaison au job, anti-rejeu et autorisation métier."""
    from .identity import DEFAULT_KEY_DIR, DEFAULT_REPLAY_DB
    if not isinstance(envelope, dict):
        raise AccessDenied("Preuve cryptographique obligatoire.")
    signed_payload = envelope.get("payload")
    expected_payload = {"permission": permission, "task_id": task_id, "handler": handler}
    if envelope.get("agent_id") != agent_id or signed_payload != expected_payload:
        raise AccessDenied("Identité ou contenu signé non lié à cette tâche.")
    try:
        if "key_version" in envelope:
            if shared_identity_verifier is not None:
                identity = shared_identity_verifier.verify(envelope)
            else:
                identity = verify_ed25519_request(envelope, public_registry, replay_db or DEFAULT_REPLAY_DB)
        else:
            identity = verify_request(envelope, key_dir or DEFAULT_KEY_DIR, replay_db or DEFAULT_REPLAY_DB)
    except (IdentityError, Ed25519IdentityError) as exc:
        raise AccessDenied(str(exc)) from exc
    active_policy = policy if policy is not None else load_policy()
    authorization = authorize_agent(agent_id, permission, agents_path, active_policy)
    return {**authorization, "identity_authenticated": True,
            "identity_algorithm": identity["algorithm"], "replay_protected": True}
