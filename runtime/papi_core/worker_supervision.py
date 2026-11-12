"""Supervision déterministe des workers PAPI — diagnostic en lecture seule."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class WorkerSupervisionError(ValueError):
    """Instantané ou seuil de supervision invalide."""


def _time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise WorkerSupervisionError(f"{field} doit être une date ISO-8601.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WorkerSupervisionError(f"{field} doit être une date ISO-8601.") from exc
    if parsed.tzinfo is None:
        raise WorkerSupervisionError(f"{field} doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise WorkerSupervisionError(f"{field} doit être un entier positif.")
    return value


def build_worker_supervision(
    jobs: list[dict[str, Any]],
    workers: list[dict[str, Any]],
    *,
    as_of: str,
    heartbeat_timeout_seconds: int = 180,
    repeated_failure_threshold: int = 3,
) -> dict[str, Any]:
    """Signale les anomalies connues sans modifier, relancer ou réaffecter."""
    now = _time(as_of, "as_of")
    heartbeat_timeout_seconds = _positive_int(heartbeat_timeout_seconds, "heartbeat_timeout_seconds")
    repeated_failure_threshold = _positive_int(repeated_failure_threshold, "repeated_failure_threshold")
    if not isinstance(jobs, list) or not isinstance(workers, list):
        raise WorkerSupervisionError("jobs et workers doivent être des listes.")

    worker_map: dict[str, dict[str, Any]] = {}
    for worker in workers:
        if not isinstance(worker, dict):
            raise WorkerSupervisionError("Définition worker invalide.")
        worker_id = worker.get("worker_id")
        if not isinstance(worker_id, str) or not worker_id or worker_id in worker_map:
            raise WorkerSupervisionError("Identifiant worker manquant ou dupliqué.")
        worker_map[worker_id] = worker

    issues: list[dict[str, Any]] = []
    worker_health = []
    for worker_id in sorted(worker_map):
        worker = worker_map[worker_id]
        status = worker.get("status", "unknown")
        if status not in {"active", "suspended", "offline", "unknown"}:
            raise WorkerSupervisionError("Statut worker inconnu.")
        identity = worker.get("identity")
        identity_valid = (
            isinstance(identity, dict)
            and identity.get("status") == "active"
            and identity.get("profile_state") == "complete"
            and isinstance(identity.get("permissions"), list)
            and isinstance(worker.get("permissions"), list)
            and set(identity["permissions"]) == set(worker["permissions"])
        )
        local = []
        if status == "offline":
            local.append(("critical", "worker_offline", "Vérifier la disponibilité et les journaux du worker."))
        elif status == "suspended":
            local.append(("warning", "worker_suspended", "Faire vérifier le statut par le responsable."))
        elif status == "unknown":
            local.append(("warning", "worker_status_unknown", "Confirmer le statut depuis une source fiable."))
        if not identity_valid:
            local.append(("critical", "identity_invalid_or_permissions_mismatch",
                          "Vérifier la fiche d’identité et la parité des permissions."))
        heartbeat = worker.get("last_heartbeat_at")
        heartbeat_state = "unknown"
        if heartbeat is None:
            local.append(("warning", "heartbeat_unverified", "Aucun heartbeat fourni ; vérifier la télémétrie."))
        else:
            last = _time(heartbeat, "last_heartbeat_at")
            age = (now - last).total_seconds()
            if age < 0:
                raise WorkerSupervisionError("Un heartbeat ne peut pas être postérieur à as_of.")
            if age > heartbeat_timeout_seconds:
                heartbeat_state = "stale"
                local.append(("critical", "heartbeat_stale", "Vérifier la connexion et les journaux ; aucune relance automatique."))
            else:
                heartbeat_state = "healthy"
        for severity, code, action in local:
            issues.append({"severity": severity, "scope": "worker", "subject_id": worker_id,
                           "code": code, "recommended_action": action, "action_executed": False})
        worker_health.append({"worker_id": worker_id, "status": status,
                              "heartbeat": heartbeat_state, "identity_valid": identity_valid,
                              "issue_count": len(local)})

    seen_jobs = set()
    for job in jobs:
        if not isinstance(job, dict) or not isinstance(job.get("id"), str) or not job["id"]:
            raise WorkerSupervisionError("Job invalide ou sans identifiant.")
        job_id = job["id"]
        if job_id in seen_jobs:
            raise WorkerSupervisionError("Identifiant job dupliqué.")
        seen_jobs.add(job_id)
        attempts = job.get("attempts", 0)
        maximum = job.get("max_attempts", 5)
        if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 0:
            raise WorkerSupervisionError("attempts doit être un entier positif ou nul.")
        if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 1 or attempts > maximum:
            raise WorkerSupervisionError("max_attempts invalide.")
        status = job.get("status")
        if status == "running":
            lease = _time(job.get("lease_until"), "lease_until")
            if lease <= now:
                issues.append({"severity": "critical", "scope": "job", "subject_id": job_id,
                               "code": "lease_expired", "recommended_action": "Examiner le worker propriétaire et le bail ; reprise manuelle après validation.",
                               "action_executed": False})
        if status in {"failed", "retry"} and attempts >= maximum:
            issues.append({"severity": "critical", "scope": "job", "subject_id": job_id,
                           "code": "retry_exhausted", "recommended_action": "Analyser la cause puis demander une approbation avant toute reprise.",
                           "action_executed": False})
        elif status in {"failed", "retry"} and attempts >= repeated_failure_threshold:
            issues.append({"severity": "warning", "scope": "job", "subject_id": job_id,
                           "code": "repeated_failures", "recommended_action": "Examiner les erreurs récentes avant toute nouvelle tentative.",
                           "action_executed": False})

    counts = {level: sum(1 for item in issues if item["severity"] == level)
              for level in ("info", "warning", "critical")}
    return {
        "as_of": now.isoformat(), "workers": worker_health, "issues": issues,
        "summary": {"workers_checked": len(worker_health), "jobs_checked": len(jobs),
                    "issues_by_severity": counts},
        "read_only": True, "mutations_performed": 0, "retries_triggered": 0,
        "leases_changed": 0, "notifications_sent": 0,
    }
