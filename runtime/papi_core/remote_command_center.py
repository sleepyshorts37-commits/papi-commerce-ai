"""Tableau de bord distant Supabase, strictement en lecture seule."""
from __future__ import annotations

from collections import Counter
from typing import Any

from .doctor import diagnose_environment
from .registry import AGENTS_FILE, load_agents
from .storage import SupabaseStore


def build_remote_command_center(
    store: SupabaseStore,
    *,
    agents_path=AGENTS_FILE,
    environ=None,
    page_size: int = 500,
    max_pages: int = 20,
) -> dict[str, Any]:
    """Construit un tableau de bord depuis Supabase sans action mutative.

    Les agents proviennent du registre local ; tâches et audit proviennent de
    Supabase. Les deux lectures distantes ne constituent pas un snapshot SQL
    transactionnel commun : l'instantané peut évoluer entre les requêtes.
    """
    if not isinstance(store, SupabaseStore):
        raise TypeError("store doit être une instance de SupabaseStore.")
    agents = load_agents(agents_path)
    tasks = store.get_tasks(page_size=page_size, max_pages=max_pages)
    histories = store.get_agent_histories(
        sorted(agents), tasks, page_size=page_size, max_pages=max_pages
    )

    agent_statuses = Counter(str(agent.get("status", "unknown")) for agent in agents.values())
    task_statuses = Counter(str(task.get("status", "unknown")) for task in tasks)
    by_agent = {agent_id: result["metrics"] for agent_id, result in histories.items()}
    totals = {
        "agents_with_activity": sum(1 for metrics in by_agent.values() if metrics["recorded_events"]),
        "tasks_assigned_attributions": sum(metrics["tasks_assigned"] for metrics in by_agent.values()),
        "tasks_completed_by_agent": sum(metrics["tasks_completed_by_agent"] for metrics in by_agent.values()),
        "tasks_blocked_by_agent": sum(metrics["tasks_blocked_by_agent"] for metrics in by_agent.values()),
        "tasks_cancelled_by_agent": sum(metrics["tasks_cancelled_by_agent"] for metrics in by_agent.values()),
        "agent_event_attributions": sum(metrics["recorded_events"] for metrics in by_agent.values()),
    }
    doctor = diagnose_environment(environ)
    return {
        "product": "PAPI COMMAND CENTER",
        "mode": "read_only_remote",
        "source": "supabase",
        "snapshot_consistency": "independent_reads_not_transactional",
        "dashboard": {
            "agents_total": len(agents),
            "agents_by_status": dict(sorted(agent_statuses.items())),
            "tasks_total": len(tasks),
            "tasks_by_status": dict(sorted(task_statuses.items())),
            "open_tasks": sum(task_statuses.get(status, 0) for status in (
                "backlog", "ready", "in_progress", "blocked", "review"
            )),
        },
        "agent_history": {
            "status": "available" if totals["agent_event_attributions"] else "no_events",
            "source": "supabase.papi_audit_events",
            "read_only": True,
            "totals": totals,
            "by_agent": by_agent,
        },
        "environment": {
            "status": doctor["status"],
            "checks": doctor["checks"],
            "secrets_displayed": False,
        },
        "controls": {
            "writes_performed": False,
            "worker_started": False,
            "external_actions_enabled": False,
            "financial_actions_enabled": False,
        },
    }
