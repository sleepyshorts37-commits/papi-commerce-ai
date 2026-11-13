"""Contrôles de gouvernance pour la délégation entre agents PAPI.

Évalue une délégation sans modifier les identités, les rôles ou les permissions.
L'appelant doit fournir un registre fiable chargé depuis la source gouvernée.
"""
from __future__ import annotations

from typing import Any


class GovernanceError(ValueError):
    """Délégation invalide ou non autorisée."""


ACTIVE_STATUSES = {"active"}
DELEGATION_PERMISSION = "delegate_tasks"


def _agent(registry: dict[str, dict[str, Any]], agent_id: str) -> dict[str, Any]:
    value = registry.get(agent_id)
    if not isinstance(value, dict) or value.get("id") != agent_id:
        raise GovernanceError("Identité absente ou incohérente.")
    return value


def _permissions(agent: dict[str, Any]) -> set[str]:
    values = agent.get("permissions")
    if not isinstance(values, list) or any(
        not isinstance(item, str) or not item.strip() for item in values
    ):
        raise GovernanceError("Liste de permissions invalide.")
    if len(values) != len(set(values)):
        raise GovernanceError("Permissions dupliquées.")
    return set(values)


def validate_hierarchy(registry: dict[str, dict[str, Any]]) -> None:
    """Refuse les responsables inconnus, l'auto-management et les cycles."""
    if not isinstance(registry, dict):
        raise GovernanceError("Registre hiérarchique invalide.")
    for agent_id, agent in registry.items():
        if not isinstance(agent, dict) or agent.get("id") != agent_id:
            raise GovernanceError("Entrée de registre incohérente.")
        manager = agent.get("manager_agent_id")
        if manager is not None and (not isinstance(manager, str) or manager not in registry):
            raise GovernanceError("Responsable hiérarchique inconnu.")
        if manager == agent_id:
            raise GovernanceError("Un agent ne peut pas être son propre responsable.")
        visited = {agent_id}
        cursor = manager
        while cursor is not None:
            if cursor in visited:
                raise GovernanceError("Cycle détecté dans la hiérarchie.")
            visited.add(cursor)
            parent = registry.get(cursor)
            if not isinstance(parent, dict):
                raise GovernanceError("Responsable hiérarchique inconnu.")
            cursor = parent.get("manager_agent_id")


def authorize_delegation(
    delegator_id: str,
    delegate_id: str,
    requested_permissions: list[str],
    registry: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Produit un reçu d'autorisation non exécutoire, sans changer les permissions."""
    validate_hierarchy(registry)
    if not isinstance(delegator_id, str) or not isinstance(delegate_id, str):
        raise GovernanceError("Identifiants de délégation invalides.")
    if delegator_id == delegate_id:
        raise GovernanceError("Auto-délégation interdite.")
    delegator = _agent(registry, delegator_id)
    delegate = _agent(registry, delegate_id)
    if delegator.get("status") not in ACTIVE_STATUSES:
        raise GovernanceError("Le délégant n'est pas actif.")
    if delegate.get("status") not in ACTIVE_STATUSES:
        raise GovernanceError("Le délégataire n'est pas actif.")
    if delegate.get("manager_agent_id") != delegator_id:
        raise GovernanceError("Seul le responsable hiérarchique direct peut déléguer.")
    delegator_permissions = _permissions(delegator)
    delegate_permissions = _permissions(delegate)
    if DELEGATION_PERMISSION not in delegator_permissions:
        raise GovernanceError("Permission delegate_tasks absente.")
    if not isinstance(requested_permissions, list) or not requested_permissions:
        raise GovernanceError("La délégation doit demander au moins une permission.")
    if any(not isinstance(item, str) or not item.strip() for item in requested_permissions):
        raise GovernanceError("Permission demandée invalide.")
    if len(requested_permissions) != len(set(requested_permissions)):
        raise GovernanceError("Permissions demandées dupliquées.")
    requested = set(requested_permissions)
    if not requested.issubset(delegator_permissions):
        raise GovernanceError("Un délégant ne peut transmettre une permission qu'il ne possède pas.")
    if not requested.issubset(delegate_permissions):
        raise GovernanceError("La délégation dépasse le plafond de permissions du délégataire.")
    return {
        "delegator_id": delegator_id,
        "delegate_id": delegate_id,
        "permissions": sorted(requested),
        "status": "authorized_for_review",
        "mutates_registry": False,
        "requires_audit": True,
    }
