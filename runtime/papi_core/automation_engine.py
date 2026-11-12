"""Read-only planner for repetitive PAPI commercial workflows.

This module proposes internal tasks from supplied snapshots. It never sends
messages, contacts clients, schedules workers, or performs external actions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping


ALLOWED_TASKS = {
    "qualify_prospects",
    "overdue_followups",
    "unresolved_client_cases",
    "weekly_commercial_report",
}


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _task(task_type: str, title: str, priority: str, details: Mapping[str, Any],
          due_at: str | None = None) -> dict[str, Any]:
    return {
        "task_type": task_type,
        "title": title,
        "priority": priority,
        "details": dict(details),
        "due_at": due_at,
        "state": "awaiting_approval",
        "requires_human_approval": True,
        "external_action": False,
    }


def build_automation_plan(
    *,
    prospects: Iterable[Mapping[str, Any]] = (),
    client_cases: Iterable[Mapping[str, Any]] = (),
    now: str | None = None,
    include_daily_qualification: bool = True,
    include_weekly_report: bool = False,
) -> dict[str, Any]:
    """Build proposed internal tasks from sanitized, pseudonymized snapshots."""
    current = _parse_datetime(now) if now else datetime.now(timezone.utc)
    if current is None:
        raise ValueError("now must be a valid ISO-8601 datetime")
    proposed: list[dict[str, Any]] = []

    if include_daily_qualification:
        proposed.append(_task(
            "qualify_prospects",
            "Review and qualify new prospects",
            "normal",
            {"instruction": "Review supplied prospect snapshot; do not contact prospects."},
        ))

    active_prospect_statuses = {
        "new", "qualified", "contact_approved", "contacted",
        "interested", "quote_prepared", "follow_up_due",
    }
    for prospect in prospects:
        status = prospect.get("status")
        due = _parse_datetime(prospect.get("next_followup_at"))
        if status not in active_prospect_statuses:
            continue
        if due and due <= current:
            proposed.append(_task(
                "overdue_followups",
                "Review an overdue prospect follow-up",
                "high",
                {"prospect_ref": prospect.get("prospect_ref"), "status": status},
                due_at=due.isoformat(),
            ))

    for case in client_cases:
        status = case.get("status")
        if status in {"open", "in_progress", "unresolved"}:
            proposed.append(_task(
                "unresolved_client_cases",
                "Review an unresolved client case",
                "high" if case.get("priority") == "high" else "normal",
                {"case_ref": case.get("case_ref"), "status": status},
            ))

    if include_weekly_report:
        proposed.append(_task(
            "weekly_commercial_report",
            "Prepare the weekly commercial performance report",
            "normal",
            {"instruction": "Use supplied aggregate metrics; distinguish estimates from verified payments."},
        ))

    proposed.sort(key=lambda item: (item["priority"] != "high", item["task_type"]))
    return {
        "generated_at": current.isoformat(),
        "budget_xof": 0,
        "execution_enabled": False,
        "tasks": proposed,
        "summary": {
            "total": len(proposed),
            "awaiting_approval": len(proposed),
            "external_actions": 0,
        },
    }


def approve_task(plan: Mapping[str, Any], task_index: int) -> dict[str, Any]:
    """Explicitly refuse execution: approval is handled outside this planner."""
    raise PermissionError(
        "This planner cannot approve or execute tasks; use the authorized human approval process."
    )
