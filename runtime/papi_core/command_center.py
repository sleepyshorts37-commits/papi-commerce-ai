"""Vue consolidée en lecture seule pour PAPI COMMAND CENTER."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .astou import build_director_brief
from .audit import read_events
from .agent_history import summarize_agent_history
from .agent_performance import build_agent_performance
from .registry import AGENTS_FILE, TASKS_FILE, load_agents, load_json
from .doctor import diagnose_environment
from .worker_scheduler import build_schedule
from .worker_supervision import build_worker_supervision
from .incident_center import build_incident_center
from .approval_center import build_approval_center
from .identity_security import validate_identity_registry
from .agent_messaging import build_message_center
from .task_delegation import build_delegation_center
from .agent_workflows import build_workflow_center
from .agent_memory import build_memory_center
from .agent_learning import build_agent_learning
from .quality_control import build_quality_control

ROOT = Path(__file__).resolve().parents[2]
AUDIT_FILE = ROOT / "data" / "events.jsonl"
IDENTITIES_FILE = ROOT / "data" / "agent-identities.json"


def build_command_center(
    tasks_path=TASKS_FILE,
    agents_path=AGENTS_FILE,
    policy_path=None,
    environ=None,
    audit_path=AUDIT_FILE,
    identities_path=IDENTITIES_FILE,
    scheduler_snapshot: dict[str, Any] | None = None,
    supervision_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Agrège registres et métriques historiques sans modifier les données."""
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

    scheduler = {
        "status": "not_configured",
        "read_only": True,
        "message": "Aucun instantané de file/worker fourni ; aucune planification calculée.",
        "plan": None,
    }
    if scheduler_snapshot is not None:
        required = {"jobs", "workers", "as_of", "handlers", "policy"}
        if not isinstance(scheduler_snapshot, dict) or set(scheduler_snapshot) != required:
            raise ValueError("scheduler_snapshot doit contenir exactement jobs, workers, as_of, handlers et policy.")
        plan = build_schedule(
            scheduler_snapshot["jobs"],
            scheduler_snapshot["workers"],
            as_of=scheduler_snapshot["as_of"],
            handlers=scheduler_snapshot["handlers"],
            policy=scheduler_snapshot["policy"],
        )
        scheduler = {
            "status": "preview_available",
            "read_only": True,
            "message": "Aperçu calculé à partir de données fournies ; aucune réservation ni exécution.",
            "plan": plan,
        }

    supervision = {
        "status": "not_configured",
        "read_only": True,
        "message": "Aucun instantané de supervision fourni ; aucun diagnostic calculé.",
        "report": None,
    }
    if supervision_snapshot is not None:
        required = {"jobs", "workers", "as_of"}
        optional = {"heartbeat_timeout_seconds", "repeated_failure_threshold"}
        if (not isinstance(supervision_snapshot, dict)
            or not required.issubset(supervision_snapshot)
            or set(supervision_snapshot) - required - optional):
            raise ValueError("supervision_snapshot doit contenir jobs, workers, as_of et éventuellement les deux seuils documentés.")
        options = {key: supervision_snapshot[key] for key in optional if key in supervision_snapshot}
        report = build_worker_supervision(
            supervision_snapshot["jobs"], supervision_snapshot["workers"],
            as_of=supervision_snapshot["as_of"], **options
        )
        supervision = {
            "status": "preview_available",
            "read_only": True,
            "message": "Diagnostic calculé à partir de données fournies ; aucune action de récupération.",
            "report": report,
        }

    events = read_events(audit_path) if audit_path is not None else []
    identity_registry = load_json(identities_path) if identities_path is not None else {"identities": []}
    identity_validation = validate_identity_registry(identity_registry)
    messages = build_message_center(events, identity_registry)
    delegations = build_delegation_center(events, identity_registry)
    workflows = build_workflow_center(events, identity_registry, agents)
    memories = build_memory_center(events, identity_registry)
    learning = build_agent_learning(agents, events, valid_tasks)
    quality_control = build_quality_control(valid_tasks, events)
    incidents = build_incident_center(events)
    approvals = build_approval_center(events)
    performance = build_agent_performance(agents, events, valid_tasks)
    per_agent = {}
    for agent_id in sorted(agents):
        summary = summarize_agent_history(agent_id, events, valid_tasks)
        per_agent[agent_id] = summary["metrics"]
    history_totals = {
        "agents_with_activity": sum(1 for metrics in per_agent.values() if metrics["recorded_events"]),
        "tasks_assigned": sum(metrics["tasks_assigned"] for metrics in per_agent.values()),
        "tasks_completed_by_agent": sum(metrics["tasks_completed_by_agent"] for metrics in per_agent.values()),
        "tasks_blocked_by_agent": sum(metrics["tasks_blocked_by_agent"] for metrics in per_agent.values()),
        "tasks_cancelled_by_agent": sum(metrics["tasks_cancelled_by_agent"] for metrics in per_agent.values()),
        "recorded_events": sum(metrics["recorded_events"] for metrics in per_agent.values()),
    }
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
        "agent_history": {
            "status": "available" if events else "no_events",
            "source": "append_only_audit_events",
            "read_only": True,
            "totals": history_totals,
            "by_agent": per_agent,
        },
        "astou_brief": brief,
        "worker_scheduler": scheduler,
        "worker_supervision": supervision,
        "incident_center": incidents,
        "approval_center": approvals,
        "agent_performance": performance,
        "agent_message_center": messages,
        "task_delegation_center": delegations,
        "agent_workflow_center": workflows,
        "agent_memory_center": memories,
        "agent_learning_engine": learning,
        "quality_control_engine": quality_control,
        "agent_identity_security": {
            **identity_validation,
            "status": "validated_documentary_registry",
            "runtime_authentication_enabled": False,
            "actions_authorized": 0,
            "actions_executed": 0,
        },
        "environment": {
            "status": doctor["status"],
            "checks": doctor["checks"],
            "network_test_performed": False,
            "secrets_displayed": False,
        },
        "controls": {
            "writes_performed": False,
            "worker_started": False,
            "scheduler_claims_performed": 0,
            "scheduler_handlers_executed": 0,
            "supervision_mutations_performed": 0,
            "supervision_retries_triggered": 0,
            "incident_writes_performed": 0,
            "incident_notifications_sent": 0,
            "approval_writes_performed": 0,
            "approval_actions_executed": 0,
            "message_writes_performed": 0,
            "messages_delivered": 0,
            "task_delegation_writes_performed": 0,
            "task_assignments_executed": 0,
            "workflow_writes_performed": 0,
            "workflow_steps_assigned": 0,
            "memory_writes_performed": 0,
            "memory_shares_performed": 0,
            "learning_records_written": 0,
            "automatic_training_runs": 0,
            "agent_behavior_changes": 0,
            "quality_reviews_created": 0,
            "quality_tasks_changed": 0,
            "external_actions_enabled": False,
            "financial_actions_enabled": False,
        },
    }
