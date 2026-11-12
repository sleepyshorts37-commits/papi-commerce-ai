"""Identités internes non forgeables par simple chaîne fournie par un appelant.

Ces objets sont des preuves de contexte en mémoire du processus. Ils ne sont pas
sérialisables et ne remplacent pas la vérification cryptographique à la frontière.
"""
from __future__ import annotations

from dataclasses import dataclass, field


_SEAL = object()


@dataclass(frozen=True)
class AuthenticatedAgentPrincipal:
    agent_id: str
    _seal: object = field(repr=False, compare=False)


def _issue_authenticated_agent_principal(agent_id: str) -> AuthenticatedAgentPrincipal:
    if not isinstance(agent_id, str) or not agent_id or len(agent_id) > 100:
        raise ValueError("Identifiant d'agent authentifié invalide.")
    return AuthenticatedAgentPrincipal(agent_id=agent_id, _seal=_SEAL)


def require_authenticated_agent_principal(value: object) -> AuthenticatedAgentPrincipal:
    if type(value) is not AuthenticatedAgentPrincipal or value._seal is not _SEAL:
        raise PermissionError("Une identité agent authentifiée est obligatoire.")
    return value
