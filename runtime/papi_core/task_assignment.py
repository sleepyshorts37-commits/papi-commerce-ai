"""Affectation contrôlée des tâches à des agents PAPI actifs."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from .agent_identity import AgentIdentityError, validate_identity_registry
from .audit import new_event


class TaskAssignmentError(PermissionError):
    """Affectation invalide ou non autorisée."""


def _active_identity(
    agent_id: str,
    agents: dict[str, dict[str, Any]],
    identity_registry: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    agent = agents.get(agent_id)
    if not isinstance(agent, dict) or agent.get("status") != "active":
        raise TaskAssignmentError(f"Agent absent ou non actif : {agent_id}.")
    cards = identity_registry.get("identities")
    matches = [
        card for card in cards
        if isinstance(card, dict) and card.get("agent_id") == agent_id
    ] if isinstance(cards, list) else []
    if len(matches) != 1:
        raise TaskAssignmentError(f"Une identité professionnelle unique est requise : {agent_id}.")
    card = matches[0]
    if card.get("status") != "active" or card.get("profile_state") != "complete":
        raise TaskAssignmentError(f"Identité inactive ou incomplète : {agent_id}.")
    if card.get("permissions") != agent.get("permissions"):
        raise TaskAssignmentError(f"Dérive des permissions détectée : {agent_id}.")
    if card.get("prohibited_actions") != agent.get("prohibited"):
        raise TaskAssignmentError(f"Dérive des interdictions détectée : {agent_id}.")
    return agent, card


def assign_task(
    task: dict[str, Any],
    *,
    assigner_id: str,
    assignee_id: str,
    agents: dict[str, dict[str, Any]],
    identity_registry: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Prépare une affectation et son événement d'audit, sans persister ni exécuter."""
    if not isinstance(task, dict) or not isinstance(agents, dict) or not isinstance(identity_registry, dict):
        raise TaskAssignmentError("Tâche et registres doivent être des objets.")
    if not isinstance(assigner_id, str) or not assigner_id.strip():
        raise TaskAssignmentError("Responsable de l'affectation non identifié.")
    if not isinstance(assignee_id, str) or not assignee_id.strip():
        raise TaskAssignmentError("Agent destinataire non identifié.")
    if not isinstance(task.get("id"), str) or not task["id"].strip():
        raise TaskAssignmentError("La tâche doit posséder un identifiant.")
    if task.get("status") in {"done", "cancelled"}:
        raise TaskAssignmentError("Une tâche terminée ou annulée ne peut être réaffectée.")
    try:
        validate_identity_registry(identity_registry, agents)
    except (AgentIdentityError, TypeError) as exc:
        raise TaskAssignmentError("Registre d'identités invalide : affectation refusée.") from exc

    assigner, assigner_card = _active_identity(assigner_id, agents, identity_registry)
    permissions = assigner.get("permissions")
    if not isinstance(permissions, list) or "assign_internal_tasks" not in permissions:
        raise TaskAssignmentError("Le responsable ne possède pas la permission assign_internal_tasks.")

    assignee, assignee_card = _active_identity(assignee_id, agents, identity_registry)
    if assignee_card.get("manager_id") != assigner_id:
        raise TaskAssignmentError("L'agent destinataire ne relève pas directement de ce responsable.")
    if assignee_id in set(assignee.get("prohibited", [])):
        raise TaskAssignmentError("Affectation interdite par le profil de l'agent.")
    if task.get("required_permission"):
        if task["required_permission"] not in assignee.get("permissions", []):
            raise TaskAssignmentError("L'agent ne possède pas la permission requise par la tâche.")

    updated = deepcopy(task)
    previous_assignee = task.get("owner_agent")
    updated["owner_agent"] = assignee_id
    updated["assigned_by"] = assigner_id
    updated["assigned_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    event = new_event(
        event_id=f"EVT-TASK-ASSIGN-{task['id']}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}",
        actor=assigner_id,
        action="task.assigned",
        entity_type="task",
        entity_id=task["id"],
        details={
            "previous_assignee": previous_assignee if isinstance(previous_assignee, str) else "",
            "new_assignee": assignee_id,
            "assigner_role": assigner_card.get("role", ""),
            "assignee_role": assignee_card.get("role", ""),
        },
    )
    return updated, event
