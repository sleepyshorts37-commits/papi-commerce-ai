"""Organigramme hiérarchique et équipes dynamiques de PAPI."""
from __future__ import annotations

from collections import defaultdict
from typing import Any


class OrganizationError(ValueError):
    """Structure hiérarchique invalide."""


def build_organization(agents: list[dict[str, Any]], owner_id: str = "president") -> dict[str, Any]:
    """Construit un organigramme validé. Ne modifie ni le registre ni les statuts."""
    if not isinstance(agents, list) or not isinstance(owner_id, str) or not owner_id.strip():
        raise OrganizationError("Registre d'agents ou identifiant du propriétaire invalide.")
    by_id: dict[str, dict[str, Any]] = {}
    normalized_ids: set[str] = set()
    for agent in agents:
        if not isinstance(agent, dict):
            raise OrganizationError("Chaque agent doit être un objet.")
        agent_id = agent.get("id")
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise OrganizationError("Identifiant agent manquant.")
        key = agent_id.casefold()
        if key == owner_id.casefold() or key in normalized_ids:
            raise OrganizationError(f"Identifiant agent dupliqué ou réservé : {agent_id}.")
        normalized_ids.add(key)
        by_id[agent_id] = agent

    children: dict[str, list[str]] = defaultdict(list)
    roots: list[str] = []
    for agent_id, agent in by_id.items():
        manager = agent.get("manager_agent_id")
        if manager is None or manager == owner_id:
            roots.append(agent_id)
            children[owner_id].append(agent_id)
        elif not isinstance(manager, str) or manager not in by_id:
            raise OrganizationError(f"Responsable inconnu pour {agent_id}: {manager}.")
        else:
            if manager == agent_id:
                raise OrganizationError(f"Un agent ne peut pas être son propre responsable : {agent_id}.")
            children[manager].append(agent_id)

    # Détection des cycles, y compris les cycles sans rattachement au propriétaire.
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(agent_id: str) -> None:
        if agent_id in visiting:
            raise OrganizationError(f"Boucle hiérarchique détectée autour de {agent_id}.")
        if agent_id in visited:
            return
        visiting.add(agent_id)
        manager = by_id[agent_id].get("manager_agent_id")
        if manager in by_id:
            visit(manager)
        visiting.remove(agent_id)
        visited.add(agent_id)

    for agent_id in by_id:
        visit(agent_id)

    return {
        "owner_id": owner_id,
        "total_agents": len(by_id),
        "root_agent_ids": sorted(roots),
        "agents": by_id,
        "teams": {key: sorted(value) for key, value in children.items()},
    }


def get_team(organization: dict[str, Any], manager_agent_id: str,
             recursive: bool = False) -> list[str]:
    """Retourne les collaborateurs directs ou tous les descendants d'un responsable."""
    if not isinstance(organization, dict):
        raise OrganizationError("Organigramme invalide.")
    agents = organization.get("agents")
    teams = organization.get("teams")
    if not isinstance(agents, dict) or not isinstance(teams, dict):
        raise OrganizationError("Organigramme incomplet.")
    if manager_agent_id != organization.get("owner_id") and manager_agent_id not in agents:
        raise OrganizationError("Responsable inconnu.")
    direct = list(teams.get(manager_agent_id, []))
    if not recursive:
        return sorted(direct)
    result: set[str] = set()
    pending = list(direct)
    while pending:
        current = pending.pop()
        if current in result:
            raise OrganizationError("Cycle détecté dans les équipes.")
        result.add(current)
        pending.extend(teams.get(current, []))
    return sorted(result)


def organization_summary(organization: dict[str, Any]) -> dict[str, Any]:
    """Fournit des métriques d'effectif et de répartition sans inventer d'agents actifs."""
    agents = organization.get("agents", {})
    departments: dict[str, int] = defaultdict(int)
    statuses: dict[str, int] = defaultdict(int)
    for agent in agents.values():
        departments[str(agent.get("department", "Non affecté"))] += 1
        statuses[str(agent.get("status", "unknown"))] += 1
    return {
        "total_agents": len(agents),
        "departments": dict(sorted(departments.items())),
        "statuses": dict(sorted(statuses.items())),
        "active_agents": statuses.get("active", 0),
    }
