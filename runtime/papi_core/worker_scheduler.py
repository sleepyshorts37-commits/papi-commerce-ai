"""Ordonnanceur déterministe PAPI — planification en lecture seule."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class WorkerSchedulerError(ValueError):
    """Entrées de planification invalides."""


_PRIORITY = {"low": 0, "normal": 1, "high": 2, "urgent": 3}


def _time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise WorkerSchedulerError(f"{field} doit être une date ISO-8601.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WorkerSchedulerError(f"{field} doit être une date ISO-8601.") from exc
    if parsed.tzinfo is None:
        raise WorkerSchedulerError(f"{field} doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)


def build_schedule(
    jobs: list[dict[str, Any]],
    workers: list[dict[str, Any]],
    *,
    as_of: str,
    handlers: dict[str, dict[str, Any]],
    policy: dict[str, Any],
    max_dispatch_per_cycle: int = 10,
    aging_interval_minutes: int = 60,
) -> dict[str, Any]:
    """Classe les jobs et propose des workers sans réserver ni exécuter.

    L'ancienneté peut faire monter progressivement une priorité (sans dépasser
    urgent). Les charges sont estimées à partir des jobs running dont le bail
    est encore valide. Les décisions ne modifient jamais les objets reçus.
    """
    now = _time(as_of, "as_of")
    if not isinstance(jobs, list) or not isinstance(workers, list):
        raise WorkerSchedulerError("jobs et workers doivent être des listes.")
    if not isinstance(handlers, dict) or not isinstance(policy, dict):
        raise WorkerSchedulerError("handlers et policy doivent être des objets.")
    if isinstance(max_dispatch_per_cycle, bool) or not isinstance(max_dispatch_per_cycle, int) or not 0 <= max_dispatch_per_cycle <= 1000:
        raise WorkerSchedulerError("max_dispatch_per_cycle doit être compris entre 0 et 1000.")
    if isinstance(aging_interval_minutes, bool) or not isinstance(aging_interval_minutes, int) or aging_interval_minutes < 1:
        raise WorkerSchedulerError("aging_interval_minutes doit être un entier positif.")

    worker_map: dict[str, dict[str, Any]] = {}
    loads: dict[str, int] = {}
    capacities: dict[str, int] = {}
    for worker in workers:
        if not isinstance(worker, dict):
            raise WorkerSchedulerError("Définition worker invalide.")
        worker_id = worker.get("worker_id")
        if not isinstance(worker_id, str) or not worker_id or worker_id in worker_map:
            raise WorkerSchedulerError("Identifiant worker manquant ou dupliqué.")
        capacity = worker.get("capacity", 1)
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            raise WorkerSchedulerError("La capacité worker doit être un entier positif.")
        worker_map[worker_id] = worker
        capacities[worker_id] = capacity
        loads[worker_id] = 0

    job_ids = set()
    claimable = []
    decisions = []
    for job in jobs:
        if not isinstance(job, dict) or not isinstance(job.get("id"), str) or not job["id"]:
            raise WorkerSchedulerError("Job invalide ou sans identifiant.")
        if job["id"] in job_ids:
            raise WorkerSchedulerError("Identifiant job dupliqué.")
        job_ids.add(job["id"])
        status = job.get("status")
        if status == "running":
            lease_until = _time(job.get("lease_until"), "lease_until")
            if lease_until > now:
                owner = job.get("lease_owner")
                if isinstance(owner, str) and owner in loads:
                    loads[owner] += 1
                decisions.append({"job_id": job["id"], "decision": "monitor",
                                  "reason": "lease_active", "worker_id": owner})
            else:
                decisions.append({"job_id": job["id"], "decision": "hold",
                                  "reason": "expired_lease_requires_recovery"})
            continue
        if status not in {"queued", "retry"}:
            decisions.append({"job_id": job["id"], "decision": "ignore",
                              "reason": "not_claimable"})
            continue
        created = _time(job.get("queued_at", job.get("created_at")), "queued_at")
        priority = job.get("priority", "normal")
        if priority not in _PRIORITY:
            raise WorkerSchedulerError("Priorité job inconnue.")
        handler_name = job.get("handler")
        handler = handlers.get(handler_name) if isinstance(handler_name, str) else None
        if not isinstance(handler, dict) or not isinstance(handler.get("permission"), str):
            decisions.append({"job_id": job["id"], "decision": "block",
                              "reason": "handler_not_registered"})
            continue
        eligible = []
        for worker_id, worker in worker_map.items():
            identity = worker.get("identity")
            permissions = worker.get("permissions")
            identity_permissions = identity.get("permissions") if isinstance(identity, dict) else None
            if (worker.get("status") == "active"
                and isinstance(identity, dict)
                and identity.get("status") == "active"
                and identity.get("profile_state") == "complete"
                and isinstance(permissions, list)
                and isinstance(identity_permissions, list)
                and set(permissions) == set(identity_permissions)
                and handler["permission"] in permissions
                and handler["permission"] not in identity.get("prohibited_actions", [])):
                eligible.append(worker_id)
        if not eligible:
            decisions.append({"job_id": job["id"], "decision": "block",
                              "reason": "no_eligible_worker"})
            continue
        age_steps = max(0, int((now - created).total_seconds() // (aging_interval_minutes * 60)))
        effective_rank = min(3, _PRIORITY[priority] + age_steps)
        claimable.append({
            "job_id": job["id"], "created": created, "priority": priority,
            "effective_priority": next(k for k, v in _PRIORITY.items() if v == effective_rank),
            "effective_rank": effective_rank, "age_steps": age_steps,
            "eligible_workers": sorted(eligible), "handler": handler,
        })

    claimable.sort(key=lambda item: (-item["effective_rank"], item["created"], item["job_id"]))
    execution_enabled = policy.get("execution_enabled") is True
    schedule = []
    for rank, item in enumerate(claimable, start=1):
        common = {
            "job_id": item["job_id"], "rank": rank,
            "priority": item["priority"], "effective_priority": item["effective_priority"],
            "age_steps": item["age_steps"],
            "eligible_workers": item["eligible_workers"],
        }
        if not execution_enabled:
            decisions.append({**common, "decision": "hold", "reason": "execution_disabled"})
            continue
        handler = item["handler"]
        if handler.get("enabled") is not True:
            decisions.append({**common, "decision": "hold", "reason": "handler_disabled"})
            continue
        if handler.get("external_action") is True and policy.get("external_actions_enabled") is not True:
            decisions.append({**common, "decision": "hold", "reason": "external_actions_disabled"})
            continue
        if len(schedule) >= max_dispatch_per_cycle:
            decisions.append({**common, "decision": "defer", "reason": "cycle_limit_reached"})
            continue
        available = [wid for wid in item["eligible_workers"] if loads[wid] < capacities[wid]]
        if not available:
            decisions.append({**common, "decision": "defer", "reason": "worker_capacity_reached"})
            continue
        selected = min(available, key=lambda wid: (loads[wid] / capacities[wid], loads[wid], wid))
        loads[selected] += 1
        candidate = {**common, "decision": "dispatch_candidate", "worker_id": selected}
        schedule.append(candidate)
        decisions.append(candidate.copy())

    return {
        "as_of": now.isoformat(),
        "schedule": schedule,
        "decisions": decisions,
        "worker_load": {wid: {"assigned_in_plan": loads[wid], "capacity": capacities[wid]}
                        for wid in sorted(loads)},
        "summary": {
            "jobs_considered": len(jobs),
            "dispatch_candidates": len(schedule),
            "read_only": True,
            "claims_performed": 0,
            "handlers_executed": 0,
            "processes_started": 0,
        },
    }
