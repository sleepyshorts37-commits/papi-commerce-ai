"""Routage déterministe : recommandations d'agents, sans affectation ni exécution."""
from __future__ import annotations

import re
from typing import Any

from .agent_identity import AgentIdentityError, validate_identity_registry


class TaskRoutingError(ValueError):
    """Entrées de routage invalides."""


def _terms(*values: Any) -> set[str]:
    text = " ".join(value for value in values if isinstance(value, str)).casefold()
    return {word for word in re.findall(r"[a-z0-9À-ÿ_-]{3,}", text)}


def recommend_assignees(
    task: dict[str, Any],
    *,
    agents: dict[str, dict[str, Any]],
    identity_registry: dict[str, Any],
    workload_by_agent: dict[str, int] | None = None,
    assigner_id: str | None = None,
) -> list[dict[str, Any]]:
    """Classe les agents actifs et éligibles. Ne modifie ni tâche ni registre.

    Score déterministe sur 100 avant pénalité de charge :
    département 40, permission requise 25, compétences 15,
    objectifs 10, rôle 10. La charge retire jusqu'à 20 points.
    """
    if not isinstance(task, dict) or not isinstance(agents, dict) or not isinstance(identity_registry, dict):
        raise TaskRoutingError("Tâche et registres doivent être des objets.")
    if not isinstance(task.get("id"), str) or not task["id"].strip():
        raise TaskRoutingError("La tâche doit posséder un identifiant.")
    if assigner_id is not None and (not isinstance(assigner_id, str) or not assigner_id.strip()):
        raise TaskRoutingError("assigner_id invalide.")
    workload = workload_by_agent or {}
    if not isinstance(workload, dict):
        raise TaskRoutingError("La charge doit être un dictionnaire agent -> nombre de tâches.")
    for agent_id, count in workload.items():
        if (not isinstance(agent_id, str) or not isinstance(count, int)
                or isinstance(count, bool) or count < 0):
            raise TaskRoutingError("Chaque charge doit être un entier positif ou nul.")

    try:
        errors = validate_identity_registry(identity_registry, agents)
        if errors:
            raise TaskRoutingError("Registre d'identités invalide : " + "; ".join(errors[:5]))
    except (AgentIdentityError, TypeError) as exc:
        raise TaskRoutingError("Registre d'identités invalide.") from exc

    required_permission = task.get("required_permission")
    if required_permission is not None and (
        not isinstance(required_permission, str) or not required_permission.strip()
    ):
        raise TaskRoutingError("required_permission invalide.")

    task_department = task.get("department")
    task_terms = _terms(task.get("title"), task.get("description"), task.get("mission"))
    cards = identity_registry["identities"]
    ranked: list[dict[str, Any]] = []

    for agent_id, agent in agents.items():
        if agent.get("status") != "active":
            continue
        matching = [card for card in cards if card.get("agent_id") == agent_id]
        if len(matching) != 1:
            continue
        card = matching[0]
        if card.get("status") != "active" or card.get("profile_state") != "complete":
            continue
        if card.get("permissions") != agent.get("permissions"):
            continue
        if card.get("prohibited_actions") != agent.get("prohibited"):
            continue
        if assigner_id is not None and card.get("manager_id") != assigner_id:
            continue
        permissions = agent.get("permissions", [])
        prohibited = agent.get("prohibited", [])
        if required_permission and (
            required_permission not in permissions or required_permission in prohibited
        ):
            continue

        score = 0
        reasons: list[str] = []
        if isinstance(task_department, str) and task_department.casefold() == str(agent.get("department", "")).casefold():
            score += 40
            reasons.append("département correspondant (+40)")
        if required_permission:
            score += 25
            reasons.append("permission requise présente (+25)")
        competencies = _terms(*(card.get("competencies") or []))
        objectives = _terms(*(card.get("objectives") or []))
        role_terms = _terms(agent.get("role"), card.get("role"))
        competence_overlap = task_terms & competencies
        objective_overlap = task_terms & objectives
        role_overlap = task_terms & role_terms
        if competence_overlap:
            score += 15
            reasons.append("compétences correspondantes (+15)")
        if objective_overlap:
            score += 10
            reasons.append("objectifs correspondants (+10)")
        if role_overlap:
            score += 10
            reasons.append("rôle correspondant (+10)")
        count = workload.get(agent_id, 0)
        penalty = min(count, 10) * 2
        score -= penalty
        reasons.append(f"charge actuelle : {count} tâche(s), pénalité -{penalty}")
        ranked.append({
            "agent_id": agent_id,
            "agent_name": agent.get("name", agent_id),
            "department": agent.get("department", ""),
            "score": score,
            "current_workload": count,
            "reasons": reasons,
        })

    return sorted(ranked, key=lambda item: (-item["score"], item["current_workload"], item["agent_id"]))
