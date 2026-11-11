"""Vue consolidée en lecture seule pour PAPI COMMAND CENTER."""
from __future__ import annotations

from collections import Counter
from typing import Any

from .astou import build_director_brief
from .registry import AGENTS_FILE, TASKS_FILE, load_agents, load_json
from .doctor import diagnose_environment


def build_command_center(
    tasks_path=TASKS_FILE,
    agents_path=AGENTS_FILE,
    policy_path=None,
    environ=None,
) -> dict[str, Any]:
    """Agrège les indicateurs locaux sans modifier les données ni lancer de worker."""
    agents = load_agents(agents_path)
    tasks_data = load_json(tasks_path)
    tasks = tasks_data.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("'tasks' doit être une liste.")
    valid_tasks = [task for task in tasks if isinstance(task, dict)]
    agent_statuses = Counter(str(agent.get("status", "unknown")) for agent in agents.values())
    task_statuses = Counter(str(task.get("status", "unknown")) for task in valid_tasks)
    brief = build_director_brief(tasks_path, agents_path, policy_path) if policy_path else build_director_brief(tasks_path, agents_path)
    doctor = diagnose_environment(environ)
    return {
        "product": "PAPI COMMAND CENTER",
        "mode": "read_only_local",
        "dashboard": {
            "agents_total": len(agents),
            "agents_by_status": dict(sorted(agent_statuses.items())),
            "tasks_total": len(valid_tasks),
            "tasks_by_status": dict(sorted(task_statuses.items())),
            "open_tasks": sum(task_statuses.get(status, 0) for status in ("backlog", "ready", "in_progress", "blocked", "review")),
            "pending_approvals": len(brief["owner_escalations"]),
            "unassigned_open_tasks": len(brief["unassigned_tasks"]),
        },
        "astou_brief": brief,
        "environment": {
            "status": doctor["status"],
            "checks": doctor["checks"],
            "network_test_performed": False,
            "secrets_displayed": False,
        },
        "controls": {
            "writes_performed": False,
            "worker_started": False,
            "external_actions_enabled": False,
            "financial_actions_enabled": False,
        },
    }
