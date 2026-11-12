"""Planificateur de cycle workers PAPI — supervision sans exécution.

Le manager produit des décisions explicables. Il ne réserve pas de jobs,
n'exécute pas de handler et ne démarre aucun processus.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class WorkerManagerError(ValueError):
    """Entrées de supervision invalides."""


def _timestamp(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise WorkerManagerError(f"{field} doit être une date ISO-8601.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WorkerManagerError(f"{field} doit être une date ISO-8601.") from exc
    if parsed.tzinfo is None:
        raise WorkerManagerError(f"{field} doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)


def build_worker_plan(
    jobs: list[dict[str, Any]],
    workers: list[dict[str, Any]],
    *,
    as_of: str,
    handlers: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    """Construit un plan de cycle en lecture seule, sans claim ni lancement.

    Un worker n'est admissible que s'il est déclaré actif, possède une identité
    complète/active et dispose de la permission du handler. Le plan n'est pas
    une autorisation d'exécuter : la politique doit aussi autoriser explicitement
    l'exécution et chaque handler doit être marqué enabled.
    """
    now = _timestamp(as_of, "as_of")
    if not isinstance(jobs, list) or not isinstance(workers, list):
        raise WorkerManagerError("jobs et workers doivent être des listes.")
    if not isinstance(handlers, dict) or not isinstance(policy, dict):
        raise WorkerManagerError("handlers et policy doivent être des objets.")
    if len({w.get("worker_id") for w in workers if isinstance(w, dict)}) != len(workers):
        raise WorkerManagerError("Identifiants workers manquants ou dupliqués.")

    worker_by_id = {}
    for worker in workers:
        if not isinstance(worker, dict) or not isinstance(worker.get("worker_id"), str):
            raise WorkerManagerError("Définition worker invalide.")
        worker_by_id[worker["worker_id"]] = worker

    decisions = []
    for job in jobs:
        if not isinstance(job, dict) or not isinstance(job.get("id"), str):
            raise WorkerManagerError("Job invalide ou sans identifiant.")
        handler_name = job.get("handler")
        handler = handlers.get(handler_name) if isinstance(handler_name, str) else None
        status = job.get("status")
        lease_until = job.get("lease_until")
        expired = False
        if status == "running" and isinstance(lease_until, str):
            expired = _timestamp(lease_until, "lease_until") <= now
        if status == "running" and not expired:
            decisions.append({"job_id": job["id"], "decision": "monitor",
                              "reason": "lease_active", "worker_id": job.get("lease_owner")})
            continue
        if status not in {"queued", "retry"} and not expired:
            decisions.append({"job_id": job["id"], "decision": "ignore",
                              "reason": "not_claimable"})
            continue
        if not isinstance(handler, dict) or not isinstance(handler.get("permission"), str):
            decisions.append({"job_id": job["id"], "decision": "block",
                              "reason": "handler_not_registered"})
            continue
        eligible = []
        for worker_id, worker in worker_by_id.items():
            identity = worker.get("identity")
            permissions = worker.get("permissions")
            if (worker.get("status") == "active"
                and isinstance(identity, dict)
                and identity.get("status") == "active"
                and identity.get("profile_state") == "complete"
                and isinstance(permissions, list)
                and handler["permission"] in permissions
                and handler["permission"] in identity.get("permissions", [])
                and handler["permission"] not in identity.get("prohibited_actions", [])):
                eligible.append(worker_id)
        if not eligible:
            decisions.append({"job_id": job["id"], "decision": "block",
                              "reason": "no_eligible_worker"})
            continue
        execution_allowed = (
            policy.get("execution_enabled") is True
            and handler.get("enabled") is True
            and policy.get("external_actions_enabled") is True
            if handler.get("external_action") is True
            else policy.get("execution_enabled") is True and handler.get("enabled") is True
        )
        if not execution_allowed:
            decisions.append({"job_id": job["id"], "decision": "hold",
                              "reason": "execution_disabled",
                              "eligible_workers": sorted(eligible)})
            continue
        decisions.append({"job_id": job["id"], "decision": "candidate",
                          "reason": "preflight_only",
                          "eligible_workers": sorted(eligible)})

    counts = {}
    for item in decisions:
        counts[item["decision"]] = counts.get(item["decision"], 0) + 1
    return {
        "as_of": now.isoformat(),
        "decisions": decisions,
        "summary": counts,
        "read_only": True,
        "claims_performed": 0,
        "handlers_executed": 0,
        "processes_started": 0,
    }
