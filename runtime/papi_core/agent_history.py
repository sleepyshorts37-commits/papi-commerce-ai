"""Historique et indicateurs factuels des agents, en lecture seule."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from .audit import AuditError, validate_event


class AgentHistoryError(ValueError):
    """Historique invalide ou incohérent."""


def _parse_aware(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise AgentHistoryError(f"{field} doit être une date ISO 8601.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AgentHistoryError(f"{field} n'est pas une date ISO 8601 valide.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AgentHistoryError(f"{field} doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)


def summarize_agent_history(
    agent_id: str,
    events: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Construit un relevé factuel à partir des événements d'audit et tâches.

    Les affectations sont attribuées au destinataire indiqué dans task.assigned.
    Les transitions sont attribuées à l'acteur signé/enregistré de l'événement.
    Aucune note subjective ni évaluation non documentée n'est créée.
    """
    if not isinstance(agent_id, str) or not agent_id.strip() or len(agent_id) > 120:
        raise AgentHistoryError("agent_id doit être un identifiant non vide.")
    if not isinstance(events, list) or not isinstance(tasks, list):
        raise AgentHistoryError("events et tasks doivent être des listes.")
    cutoff = _parse_aware(as_of, "as_of") if as_of is not None else datetime.now(timezone.utc)

    task_by_id: dict[str, dict[str, Any]] = {}
    for task in tasks:
        if not isinstance(task, dict) or not isinstance(task.get("id"), str):
            raise AgentHistoryError("Chaque tâche doit être un objet avec un id textuel.")
        if task["id"] in task_by_id:
            raise AgentHistoryError(f"Tâche dupliquée : {task['id']}.")
        task_by_id[task["id"]] = task

    seen: set[str] = set()
    parsed_events: list[tuple[datetime, dict[str, Any]]] = []
    for event in events:
        try:
            validate_event(event)
        except (AuditError, TypeError) as exc:
            raise AgentHistoryError(f"Événement d'audit invalide : {exc}") from exc
        if event["event_id"] in seen:
            raise AgentHistoryError(f"Événement dupliqué : {event['event_id']}.")
        seen.add(event["event_id"])
        moment = _parse_aware(event["occurred_at"], "occurred_at")
        if moment <= cutoff:
            parsed_events.append((moment, event))
    parsed_events.sort(key=lambda item: (item[0], item[1]["event_id"]))

    records: list[dict[str, Any]] = []
    assigned_ids: set[str] = set()
    transitions = Counter()
    durations: list[float] = []
    blocked = cancelled = completed = 0

    for moment, event in parsed_events:
        if event["entity_type"] != "task":
            continue
        task_id = event["entity_id"]
        details = event["details"]
        action = event["action"]
        relevant = False
        record_type = action
        if action == "task.assigned" and details.get("new_assignee") == agent_id:
            relevant = True
            assigned_ids.add(task_id)
        elif action == "task.status_changed" and event["actor"] == agent_id:
            relevant = True
            old_status = details.get("from_status")
            new_status = details.get("to_status")
            if not isinstance(new_status, str) or not isinstance(old_status, str):
                raise AgentHistoryError("Transition d'état sans from_status/to_status.")
            transitions[f"{old_status}->{new_status}"] += 1
            if new_status == "done":
                completed += 1
                task = task_by_id.get(task_id, {})
                created = task.get("created_at")
                if created is not None:
                    start = _parse_aware(created, f"tasks[{task_id}].created_at")
                    elapsed = (moment - start).total_seconds()
                    if elapsed < 0:
                        raise AgentHistoryError("Une tâche ne peut être terminée avant sa création.")
                    durations.append(elapsed)
            elif new_status == "blocked":
                blocked += 1
            elif new_status == "cancelled":
                cancelled += 1
        elif action.startswith("task.approval_") and event["actor"] == agent_id:
            relevant = True

        if relevant:
            records.append({
                "event_id": event["event_id"],
                "occurred_at": moment.isoformat().replace("+00:00", "Z"),
                "type": record_type,
                "task_id": task_id,
                "actor": event["actor"],
            })

    average_seconds = round(sum(durations) / len(durations), 2) if durations else None
    return {
        "agent_id": agent_id,
        "as_of": cutoff.isoformat().replace("+00:00", "Z"),
        "source": "append_only_audit_events",
        "read_only": True,
        "metrics": {
            "tasks_assigned": len(assigned_ids),
            "tasks_completed_by_agent": completed,
            "tasks_blocked_by_agent": blocked,
            "tasks_cancelled_by_agent": cancelled,
            "status_transitions_by_agent": sum(transitions.values()),
            "transitions": dict(sorted(transitions.items())),
            "average_completion_seconds": average_seconds,
            "completion_samples": len(durations),
            "recorded_events": len(records),
        },
        "history": records,
        "evaluation": {
            "status": "insufficient_evidence" if not records else "metrics_only",
            "subjective_score": None,
            "note": "Aucune note subjective n'est calculée. Les évaluations humaines documentées restent séparées.",
        },
    }
