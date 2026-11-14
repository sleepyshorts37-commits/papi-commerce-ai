"""Vue consolidée en lecture seule pour PAPI COMMAND CENTER."""
from __future__ import annotations
from collections import Counter
from typing import Any
from .astou import build_director_brief
from .registry import AGENTS_FILE, TASKS_FILE, load_agents, load_json
from .doctor import diagnose_environment
from .workers_report import build_workers_report
from .workers_inputs import build_workers_inputs

def build_command_center(tasks_path=TASKS_FILE, agents_path=AGENTS_FILE, policy_path=None, environ=None, *,
                         platform_candidates=None, handoffs=None, profitability_results=None,
                         platform_discovery_batch=None, handoff_records=None, profitability_batch=None) -> dict[str, Any]:
    """Aggregate local registries and explicit worker outputs without side effects."""
    agents = load_agents(agents_path)
    tasks_data = load_json(tasks_path)
    tasks = tasks_data.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("tasks doit être une liste")
    valid_tasks = [task for task in tasks if isinstance(task, dict)]
    agent_statuses = Counter(str(agent.get("status", "unknown")) for agent in agents.values())
    task_statuses = Counter(str(task.get("status", "unknown")) for task in valid_tasks)
    brief = build_director_brief(tasks_path, agents_path, policy_path) if policy_path else build_director_brief(tasks_path, agents_path)
    doctor = diagnose_environment(environ)

    raw_values = (platform_candidates, handoffs, profitability_results)
    source_values = (platform_discovery_batch, handoff_records, profitability_batch)
    if any(raw is not None and source is not None for raw, source in zip(raw_values, source_values)):
        raise ValueError("Fournir une seule forme de données par source.")

    adapted = build_workers_inputs(platform_discovery_batch=platform_discovery_batch,
                                   handoff_records=handoff_records, profitability_batch=profitability_batch)
    workers = build_workers_report(
        platform_candidates=platform_candidates if platform_candidates is not None else adapted["platform_candidates"],
        handoffs=handoffs if handoffs is not None else adapted["handoffs"],
        profitability_results=profitability_results if profitability_results is not None else adapted["profitability_results"],
    )
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
        "ai_workers": workers,
        "ai_workers_sources": adapted["sources"],
        "environment": {"status": doctor["status"], "checks": doctor["checks"],
                        "network_test_performed": False, "secrets_displayed": False},
        "controls": {"writes_performed": False, "worker_started": False,
                     "external_actions_enabled": False, "financial_actions_enabled": False,
                     "notifications_sent": False},
    }
