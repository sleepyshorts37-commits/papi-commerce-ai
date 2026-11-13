"""Agrégation sûre de snapshots de file fournis par un collecteur externe.

Ce module est pur : aucun accès DB/réseau, aucune métrique inventée et aucun payload
ou identifiant de job n'est recopié dans le rapport.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class QueueObservabilityError(ValueError):
    """Snapshot de file invalide."""


STATUSES = ("queued", "running", "retry", "done", "failed")


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise QueueObservabilityError(f"{field} doit être un horodatage ISO.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QueueObservabilityError(f"{field} invalide.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise QueueObservabilityError(f"{field} doit inclure un fuseau.")
    return parsed


def evaluate_queue_snapshot(
    jobs: list[dict[str, Any]],
    *,
    now: datetime | None = None,
    stale_running_seconds: int = 900,
) -> dict[str, Any]:
    """Produit des compteurs et alertes synthétiques depuis un snapshot explicite."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise QueueObservabilityError("now doit inclure un fuseau horaire.")
    if type(stale_running_seconds) is not int or stale_running_seconds <= 0:
        raise QueueObservabilityError("stale_running_seconds doit être positif.")
    if not isinstance(jobs, list):
        raise QueueObservabilityError("jobs doit être une liste.")

    counts = {status: 0 for status in STATUSES}
    seen: set[str] = set()
    active_ages: list[int] = []
    stale_running = 0
    exhausted_active = 0
    due_retries = 0
    retry_delays: list[int] = []

    for job in jobs:
        if not isinstance(job, dict):
            raise QueueObservabilityError("Chaque job doit être un objet.")
        job_id, status = job.get("id"), job.get("status")
        if not isinstance(job_id, str) or not job_id.strip() or len(job_id) > 160:
            raise QueueObservabilityError("Identifiant de job invalide.")
        if job_id in seen:
            raise QueueObservabilityError("Identifiant de job dupliqué.")
        seen.add(job_id)
        if status not in STATUSES:
            raise QueueObservabilityError("Statut de job non pris en charge.")
        counts[status] += 1
        attempts, maximum = job.get("attempts"), job.get("max_attempts")
        if type(attempts) is not int or type(maximum) is not int or attempts < 0 or not 1 <= maximum <= 10 or attempts > maximum:
            raise QueueObservabilityError("Métadonnées de tentative invalides.")

        if status in ("queued", "retry"):
            created = _timestamp(job.get("created_at"), "created_at")
            age = (current - created.astimezone(current.tzinfo)).total_seconds()
            active_ages.append(max(0, int(age)))
        if status == "retry":
            available = _timestamp(job.get("available_at"), "available_at")
            delay = int((available - current).total_seconds())
            if delay <= 0:
                due_retries += 1
            else:
                retry_delays.append(delay)
        if status == "running":
            lease_until = _timestamp(job.get("lease_until"), "lease_until")
            if (current - lease_until.astimezone(current.tzinfo)).total_seconds() > 0:
                stale_running += 1
        if status in ("queued", "retry", "running") and attempts >= maximum:
            exhausted_active += 1

    alert_reasons = []
    if stale_running:
        alert_reasons.append("expired_running_lease")
    if exhausted_active:
        alert_reasons.append("active_job_at_attempt_ceiling")
    return {
        "overall_status": "degraded" if alert_reasons else "healthy",
        "observed_at": current.isoformat(),
        "total_jobs": len(jobs),
        "counts": counts,
        "active_backlog": counts["queued"] + counts["retry"] + counts["running"],
        "oldest_queued_or_retry_age_seconds": max(active_ages, default=None),
        "due_retries": due_retries,
        "next_retry_in_seconds": min(retry_delays, default=None),
        "expired_running_leases": stale_running,
        "active_jobs_at_attempt_ceiling": exhausted_active,
        "alert_reasons": alert_reasons,
        "source_snapshot_only": True,
        "database_or_network_access_performed": False,
        "job_payloads_or_identifiers_included": False,
    }
