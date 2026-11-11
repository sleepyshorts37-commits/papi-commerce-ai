"""Planificateur déterministe : propose des affectations sans lancer d'agents."""
from __future__ import annotations

from typing import Any
from .registry import load_agents, load_json, TASKS_FILE

PRIORITY_ORDER = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
QUEUE_STATUSES = {"backlog", "ready"}


def build_dispatch_plan(tasks_path=TASKS_FILE, agents_path=None) -> dict[str, Any]:
    """Construit un plan consultatif. N'écrit rien et n'exécute aucune tâche."""
    agents = load_agents(agents_path) if agents_path else load_agents()
    data = load_json(tasks_path)
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("'tasks' doit être une liste.")
    proposals = []
    for task in sorted(
        (item for item in tasks if isinstance(item, dict) and item.get("status") in QUEUE_STATUSES),
        key=lambda item: (PRIORITY_ORDER.get(item.get("priority"), 99), item.get("created_at", ""), item.get("id", "")),
    ):
        department = str(task.get("department", ""))
        candidates = [
            {"id": agent["id"], "name": agent["name"], "status": agent.get("status", "unknown")}
            for agent in agents.values()
            if str(agent.get("department", "")).casefold() == department.casefold()
        ]
        approval = task.get("approval_required") is True and task.get("approval_status") != "approved"
        active = [candidate for candidate in candidates if candidate["status"] == "active"]
        if approval:
            reason = "approval_required"
        elif not active:
            reason = "no_deployed_agent"
        else:
            reason = "ready_for_owner_review"
        proposals.append({
            "task_id": task.get("id"),
            "priority": task.get("priority"),
            "department": department,
            "candidate_agents": candidates,
            "dispatch_allowed": False,
            "blocking_reason": reason,
        })
    return {
        "mode": "proposal_only",
        "agent_execution_status": "not_deployed",
        "external_actions_enabled": False,
        "proposals": proposals,
        "note": "Aucune affectation réelle, écriture, communication externe ou exécution d'agent n'est effectuée.",
    }
