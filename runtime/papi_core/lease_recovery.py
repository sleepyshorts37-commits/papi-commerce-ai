"""Évaluation locale et déterministe des états de bail de la file.

Cette fonction décrit une décision de récupération à partir d'un instantané ;
elle ne réserve, ne renouvelle et ne modifie aucun travail.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


class LeaseRecoveryError(ValueError):
    """Instantané de bail invalide."""


def _aware_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise LeaseRecoveryError(f"{field} doit être un horodatage ISO.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LeaseRecoveryError(f"{field} invalide.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise LeaseRecoveryError(f"{field} doit inclure un fuseau.")
    return parsed


def assess_lease_recovery(
    job: dict[str, Any], *, now: datetime
) -> dict[str, Any]:
    """Classe un bail sans exposer son jeton ni son propriétaire."""
    if not isinstance(job, dict):
        raise LeaseRecoveryError("job doit être un objet.")
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise LeaseRecoveryError("now doit être un datetime avec fuseau.")
    status = job.get("status")
    if status not in {"queued", "retry", "running", "done", "failed"}:
        raise LeaseRecoveryError("Statut de job invalide.")
    attempts, maximum = job.get("attempts"), job.get("max_attempts")
    if (type(attempts) is not int or type(maximum) is not int
            or attempts < 0 or not 1 <= maximum <= 10 or attempts > maximum):
        raise LeaseRecoveryError("Métadonnées de tentative invalides.")

    if status != "running":
        return {
            "decision": "not_running",
            "claim_eligible": status in {"queued", "retry"} and attempts < maximum,
            "terminal": status in {"done", "failed"},
            "reason": "not_running",
            "lease_token_exposed": False,
        }

    expiry = _aware_timestamp(job.get("lease_until"), "lease_until")
    expired = expiry <= now.astimezone(expiry.tzinfo)
    if not expired:
        return {
            "decision": "wait_for_lease_expiry",
            "claim_eligible": False,
            "terminal": False,
            "reason": "lease_still_valid",
            "lease_token_exposed": False,
        }
    if attempts >= maximum:
        return {
            "decision": "terminalize",
            "claim_eligible": False,
            "terminal": True,
            "reason": "lease_expired_at_attempt_ceiling",
            "lease_token_exposed": False,
        }
    return {
        "decision": "reclaim",
        "claim_eligible": True,
        "terminal": False,
        "reason": "lease_expired_attempts_remaining",
        "lease_token_exposed": False,
    }
