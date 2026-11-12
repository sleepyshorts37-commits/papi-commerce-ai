"""Contrôle d'accès fail-closed pour la messagerie PAPI."""
from __future__ import annotations

from pathlib import Path

from .registry import AGENTS_FILE, load_agents


class ChatAuthorizationError(PermissionError):
    """Action de messagerie non autorisée."""


_OWNER_PERMISSIONS = {"chat.send", "chat.receive", "chat.broadcast", "chat.read", "chat.read_all"}


def _permissions(agent_id: str, agents_path: Path) -> set[str]:
    if agent_id == "owner":
        return set(_OWNER_PERMISSIONS)
    agents = load_agents(agents_path)
    agent = agents.get(agent_id)
    if not isinstance(agent, dict) or agent.get("status") != "active":
        raise ChatAuthorizationError("Agent absent ou non actif : accès refusé.")
    values = agent.get("permissions")
    if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
        raise ChatAuthorizationError("Permissions absentes ou invalides : accès refusé.")
    return set(values)


def require_permission(agent_id: str, permission: str, agents_path: Path = AGENTS_FILE) -> None:
    if permission not in _permissions(agent_id, agents_path):
        raise ChatAuthorizationError(f"Permission requise : {permission}.")


def authorize_send(sender: str, recipient: str, agents_path: Path = AGENTS_FILE) -> None:
    require_permission(sender, "chat.send", agents_path)
    if recipient == "all":
        require_permission(sender, "chat.broadcast", agents_path)
        return
    if recipient != "owner":
        require_permission(recipient, "chat.receive", agents_path)
