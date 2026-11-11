"""Briefing deterministe de direction prepare par Astou, sans IA distante ni action."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .registry import AGENTS_FILE, TASKS_FILE, load_agents, load_json

POLICY_FILE = Path(__file__).resolve().parents[2] / "config" / "policy.json"


def build_director_brief(
    tasks_path: Path = TASKS_FILE,
    agents_path: Path = AGENTS_FILE,
    policy_path: Path = POLICY_FILE,
) -> dict[str, Any]:
    """Produit un état factuel et des alertes; ne modifie aucun registre."""
    agents = load_agents(agents_path)
    task_data = load_json(tasks_path)
    policy = load_json(policy_path)
    tasks = task_data.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("'tasks' doit être une liste.")

    valid_tasks = [item for item in tasks if isinstance(item, dict)]
    task_counts = Counter(str(item.get("status", "unknown")) for item in valid_tasks)
    active_agents = [item for item in agents.values() if item.get("status") == "active"]
    pending_approvals = [
        {"task_id": item.get("id"), "title": item.get("title", ""),
         "department": item.get("department", "")}
        for item in valid_tasks
        if item.get("approval_required") is True and item.get("approval_status") != "approved"
        and item.get("status") not in {"done", "cancelled"}
    ]
    unassigned = [
        {"task_id": item.get("id"), "title": item.get("title", "")}
        for item in valid_tasks
        if item.get("status") in {"backlog", "ready"}
        and not any(agent.get("id") == item.get("owner_agent") for agent in agents.values())
    ]
    recommendations = []
    if pending_approvals:
        recommendations.append("Soumettre les approbations en attente au propriétaire avant toute exécution.")
    if not active_agents:
        recommendations.append("Aucun agent n'est déployé : conserver les affectations au stade de proposition.")
    if unassigned:
        recommendations.append("Faire examiner les tâches sans responsable valide par Marietou.")
    if not recommendations:
        recommendations.append("Examiner les priorités ouvertes et demander une revue qualité avant clôture.")

    return {
        "prepared_by": "astou",
        "mode": "deterministic_read_only",
        "source": "local_project_registries",
        "facts": {
            "agent_count": len(agents),
            "active_agent_count": len(active_agents),
            "task_count": len(valid_tasks),
            "task_status_counts": dict(sorted(task_counts.items())),
            "execution_enabled": policy.get("execution_enabled") is True,
            "external_actions_enabled": policy.get("external_actions_enabled") is True,
        },
        "owner_escalations": pending_approvals,
        "unassigned_tasks": unassigned,
        "recommendations": recommendations,
        "limitations": [
            "Aucune recherche externe ni analyse par modèle IA n'a été effectuée.",
            "Aucune tâche n'a été affectée, modifiée ou exécutée.",
            "Les agents déclarés active dans le registre ne prouvent pas à eux seuls un déploiement réel.",
        ],
    }
