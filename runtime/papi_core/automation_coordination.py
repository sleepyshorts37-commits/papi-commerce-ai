"""Read-only coordination layer for PAPI department automation plans.

It consolidates proposed internal tasks, removes duplicates and marks tasks
blocked when their declared prerequisites are not complete. It never executes.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping


VALID_PRIORITIES = {"low", "normal", "high", "urgent"}
VALID_STATES = {"proposed", "awaiting_approval", "blocked"}


def _stable_task_id(department: str, task_type: str, reference: str) -> str:
    raw = "|".join((department.strip().lower(), task_type.strip(), reference.strip()))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"PAPI-TASK-{digest.upper()}"


def _reference(task: Mapping[str, Any]) -> str:
    details = task.get("details")
    if isinstance(details, Mapping):
        for key in ("prospect_ref", "case_ref", "client_ref", "service_ref", "record_ref"):
            value = details.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return str(task.get("reference") or task.get("title") or "general").strip()


def coordinate_department_plans(
    department_plans: Mapping[str, Iterable[Mapping[str, Any]]],
    *,
    completed_task_ids: Iterable[str] = (),
) -> dict[str, Any]:
    """Consolidate sanitized department tasks into one approval queue."""
    completed = set(completed_task_ids)
    consolidated: dict[str, dict[str, Any]] = {}
    rejected = 0
    duplicates = 0

    for department, tasks in department_plans.items():
        if not isinstance(department, str) or not department.strip():
            rejected += 1
            continue
        for task in tasks:
            if not isinstance(task, Mapping):
                rejected += 1
                continue
            task_type = task.get("task_type")
            title = task.get("title")
            priority = task.get("priority", "normal")
            if not isinstance(task_type, str) or not task_type.strip():
                rejected += 1
                continue
            if not isinstance(title, str) or not title.strip():
                rejected += 1
                continue
            if priority not in VALID_PRIORITIES:
                rejected += 1
                continue

            reference = _reference(task)
            task_id = _stable_task_id(department, task_type, reference)
            if task_id in consolidated:
                duplicates += 1
                continue

            raw_dependencies = task.get("depends_on", [])
            if not isinstance(raw_dependencies, (list, tuple)) or not all(
                isinstance(item, str) and item.strip() for item in raw_dependencies
            ):
                rejected += 1
                continue
            dependencies = sorted(set(raw_dependencies))
            missing = [item for item in dependencies if item not in completed]
            state = "blocked" if missing else "awaiting_approval"

            details = task.get("details", {})
            if not isinstance(details, Mapping):
                rejected += 1
                continue

            consolidated[task_id] = {
                "task_id": task_id,
                "department": department.strip(),
                "task_type": task_type.strip(),
                "title": title.strip(),
                "priority": priority,
                "reference": reference,
                "details": dict(details),
                "depends_on": dependencies,
                "blocked_by": missing,
                "state": state,
                "requires_human_approval": True,
                "external_action": False,
            }

    priority_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
    tasks_out = sorted(
        consolidated.values(),
        key=lambda item: (item["state"] != "blocked",
                          priority_order[item["priority"]],
                          item["department"], item["task_id"]),
    )
    counts = {state: sum(task["state"] == state for task in tasks_out)
              for state in ("awaiting_approval", "blocked")}
    return {
        "execution_enabled": False,
        "budget_xof": 0,
        "tasks": tasks_out,
        "summary": {
            "total_received": sum(len(list(items)) if not isinstance(items, list) else len(items)
                                  for items in department_plans.values()),
            "total_unique": len(tasks_out),
            "duplicates_removed": duplicates,
            "rejected_invalid": rejected,
            "awaiting_approval": counts["awaiting_approval"],
            "blocked": counts["blocked"],
            "external_actions": 0,
        },
    }
