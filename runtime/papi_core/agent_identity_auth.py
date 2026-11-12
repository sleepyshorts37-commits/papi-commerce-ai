"""Authentification Ed25519 liée à une carte d'identité PAPI active."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agent_identity import validate_identity_registry
from .identity_ed25519 import verify_ed25519_request
from .registry import AGENTS_FILE


class AgentIdentityAuthenticationError(PermissionError):
    """Carte d'identité absente, incohérente ou non activée."""


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IDENTITIES_FILE = ROOT / "data" / "agent-identities.json"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgentIdentityAuthenticationError(
            "Registre d'identités absent ou illisible : accès fermé."
        ) from exc
    if not isinstance(value, dict):
        raise AgentIdentityAuthenticationError("Registre d'identités invalide : accès fermé.")
    return value


def authenticate_agent_request(
    envelope: dict[str, Any],
    *,
    identities_path: Path = DEFAULT_IDENTITIES_FILE,
    agents_path: Path = AGENTS_FILE,
    public_registry_path: Path,
    replay_db: Path,
) -> dict[str, Any]:
    """Vérifie la carte active, sa cohérence de permissions, puis la signature et le nonce.

    Les cartes planifiées/incomplètes ne peuvent jamais authentifier un agent.
    Les clés privées restent locales et ne sont jamais lues par cette fonction.
    """
    if not isinstance(envelope, dict) or not isinstance(envelope.get("agent_id"), str):
        raise AgentIdentityAuthenticationError("Enveloppe agent invalide : accès fermé.")

    identities = _read_json(identities_path)
    agents_doc = _read_json(agents_path)
    agents_list = agents_doc.get("agents")
    if not isinstance(agents_list, list):
        raise AgentIdentityAuthenticationError("Registre agents invalide : accès fermé.")
    agents = {
        item.get("id"): item for item in agents_list
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    errors = validate_identity_registry(identities, agents)
    if errors:
        raise AgentIdentityAuthenticationError("Registre des cartes invalide : accès fermé.")

    agent_id = envelope["agent_id"]
    cards = [
        card for card in identities["identities"]
        if isinstance(card, dict) and card.get("agent_id") == agent_id
    ]
    if len(cards) != 1:
        raise AgentIdentityAuthenticationError("Carte unique de l'agent introuvable : accès fermé.")
    card = cards[0]
    if card.get("status") != "active" or card.get("profile_state") != "complete":
        raise AgentIdentityAuthenticationError("Carte non activée ou incomplète : accès fermé.")

    agent = agents.get(agent_id)
    if not isinstance(agent, dict) or agent.get("status") != "active":
        raise AgentIdentityAuthenticationError("Agent non actif dans le registre : accès fermé.")
    if card.get("permissions") != agent.get("permissions", []):
        raise AgentIdentityAuthenticationError("Permissions de la carte divergentes : accès fermé.")
    if card.get("prohibited_actions") != agent.get("prohibited", []):
        raise AgentIdentityAuthenticationError("Interdictions de la carte divergentes : accès fermé.")

    result = verify_ed25519_request(
        envelope, registry_path=public_registry_path, replay_db=replay_db
    )
    return {**result, "identity_id": card["identity_id"], "identity_verified": True}
