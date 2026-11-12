"""Primitives de bail temporaire pour une future file de workers PAPI.

Les fonctions sont pures : elles retournent une copie de tâche et un événement.
Elles ne garantissent pas l'exclusion mutuelle sans persistance transactionnelle.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from .audit import new_event


class TaskLeaseError(PermissionError):
    """Bail de tâche invalide, expiré ou détenu par un autre worker."""


MIN_LEASE_SECONDS = 30
MAX_LEASE_SECONDS = 3600


def _instant(value: str | datetime) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise TaskLeaseError("Horodatage ISO 8601 invalide.") from exc
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise TaskLeaseError("Un horodatage avec fuseau horaire est obligatoire.")
    return value.astimezone(timezone.utc)


def _duration(seconds: int) -> int:
    if isinstance(seconds, bool) or not isinstance(seconds, int) or not MIN_LEASE_SECONDS <= seconds <= MAX_LEASE_SECONDS:
        raise TaskLeaseError(f"La durée du bail doit être comprise entre {MIN_LEASE_SECONDS} et {MAX_LEASE_SECONDS} secondes.")
    return seconds


def _event(task: dict[str, Any], actor: str, action: str, details: dict[str, Any]) -> dict[str, Any]:
    return new_event(
        event_id=f"EVT-{uuid4().hex.upper()}",
        actor=actor,
        action=action,
        entity_type="task",
        entity_id=task["id"],
        details=details,
    )


def claim_task(
    task: dict[str, Any],
    agent: dict[str, Any],
    *,
    lease_id: str,
    now: str | datetime,
    lease_seconds: int = 300,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Réserve une tâche ready au worker propriétaire, sans lancer son traitement."""
    if not isinstance(task, dict) or not isinstance(agent, dict):
        raise TaskLeaseError("Tâche et agent doivent être des objets.")
    worker_id = agent.get("id")
    if not isinstance(worker_id, str) or not worker_id.strip() or agent.get("status") != "active":
        raise TaskLeaseError("Le worker doit être identifié et actif.")
    if task.get("status") != "ready":
        raise TaskLeaseError("Seule une tâche ready peut être réservée.")
    if task.get("owner_agent") != worker_id:
        raise TaskLeaseError("Le worker n'est pas le propriétaire affecté à cette tâche.")
    if task.get("approval_required") is True and task.get("approval_status") != "approved":
        raise TaskLeaseError("Approbation propriétaire requise avant réservation.")
    if not isinstance(task.get("id"), str) or not task["id"].strip():
        raise TaskLeaseError("Identifiant de tâche absent.")
    if not isinstance(lease_id, str) or not lease_id.strip() or len(lease_id) > 120:
        raise TaskLeaseError("Identifiant de bail invalide.")
    instant = _instant(now)
    duration = _duration(lease_seconds)
    expires = instant + timedelta(seconds=duration)
    updated = deepcopy(task)
    updated["status"] = "in_progress"
    updated["worker_lease"] = {
        "lease_id": lease_id,
        "worker_id": worker_id,
        "claimed_at": instant.isoformat().replace("+00:00", "Z"),
        "heartbeat_at": instant.isoformat().replace("+00:00", "Z"),
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
    }
    event = _event(updated, worker_id, "task.lease_claimed", {
        "worker_id": worker_id, "lease_id": lease_id, "lease_seconds": duration,
    })
    return updated, event


def heartbeat_task(
    task: dict[str, Any],
    *,
    worker_id: str,
    lease_id: str,
    now: str | datetime,
    lease_seconds: int = 300,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Renouvelle un bail encore valide détenu par le même worker."""
    if not isinstance(task, dict) or task.get("status") != "in_progress":
        raise TaskLeaseError("La tâche n'est pas en cours.")
    lease = task.get("worker_lease")
    if not isinstance(lease, dict) or lease.get("worker_id") != worker_id or lease.get("lease_id") != lease_id:
        raise TaskLeaseError("Bail absent ou détenu par un autre worker.")
    instant = _instant(now)
    expires_at = _instant(lease.get("expires_at"))
    if instant >= expires_at:
        raise TaskLeaseError("Le bail a expiré ; renouvellement refusé.")
    duration = _duration(lease_seconds)
    updated = deepcopy(task)
    updated_lease = dict(lease)
    updated_lease["heartbeat_at"] = instant.isoformat().replace("+00:00", "Z")
    updated_lease["expires_at"] = (instant + timedelta(seconds=duration)).isoformat().replace("+00:00", "Z")
    updated["worker_lease"] = updated_lease
    event = _event(updated, worker_id, "task.lease_heartbeat", {
        "worker_id": worker_id, "lease_id": lease_id, "lease_seconds": duration,
    })
    return updated, event


def expire_task_lease(
    task: dict[str, Any],
    *,
    now: str | datetime,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Remet une tâche réservée en ready si et seulement si son bail est expiré."""
    if not isinstance(task, dict):
        raise TaskLeaseError("La tâche doit être un objet.")
    lease = task.get("worker_lease")
    if task.get("status") != "in_progress" or not isinstance(lease, dict):
        return None
    instant = _instant(now)
    expires_at = _instant(lease.get("expires_at"))
    if instant < expires_at:
        return None
    worker_id = lease.get("worker_id")
    if not isinstance(worker_id, str) or not worker_id:
        raise TaskLeaseError("Détenteur du bail invalide ; réinitialisation refusée.")
    updated = deepcopy(task)
    updated["status"] = "ready"
    updated.pop("worker_lease", None)
    event = _event(updated, "system", "task.lease_expired", {
        "previous_worker_id": worker_id,
        "lease_id": str(lease.get("lease_id", ""))[:120],
    })
    return updated, event
