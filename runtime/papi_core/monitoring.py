"""Évaluation déterministe de signaux de santé fournis par les composants.

Aucun appel réseau, aucune collecte automatique et aucune action corrective ne sont
effectués ici. Les sondes sont injectées par l'appelant et leurs détails ne sont
jamais recopiés dans le rapport.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

VALID_STATES = {"healthy", "degraded", "unavailable", "unknown"}
SEVERITY = {"healthy": 0, "unknown": 1, "degraded": 2, "unavailable": 3}


class MonitoringError(ValueError):
    """Entrée de surveillance invalide."""


def evaluate_health_snapshot(
    checks: list[dict[str, Any]],
    *,
    now: datetime | None = None,
    stale_after_seconds: int = 300,
) -> dict[str, Any]:
    """Évalue une liste de signaux horodatés sans contacter les systèmes surveillés."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise MonitoringError("now doit inclure un fuseau horaire.")
    if isinstance(stale_after_seconds, bool) or not isinstance(stale_after_seconds, int) or stale_after_seconds <= 0:
        raise MonitoringError("stale_after_seconds doit être un entier strictement positif.")
    if not isinstance(checks, list):
        raise MonitoringError("checks doit être une liste.")

    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    for check in checks:
        if not isinstance(check, dict):
            raise MonitoringError("Chaque signal doit être un objet.")
        check_id = check.get("id")
        state = check.get("status")
        observed = check.get("observed_at")
        if not isinstance(check_id, str) or not check_id.strip() or len(check_id) > 100:
            raise MonitoringError("Identifiant de signal invalide.")
        if check_id in seen:
            raise MonitoringError("Identifiant de signal dupliqué.")
        seen.add(check_id)
        if state not in VALID_STATES:
            raise MonitoringError(f"État invalide pour le signal {check_id}.")
        if not isinstance(observed, str):
            raise MonitoringError(f"Horodatage manquant pour le signal {check_id}.")
        try:
            timestamp = datetime.fromisoformat(observed.replace("Z", "+00:00"))
        except ValueError as exc:
            raise MonitoringError(f"Horodatage invalide pour le signal {check_id}.") from exc
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise MonitoringError(f"Horodatage sans fuseau pour le signal {check_id}.")

        age = (current - timestamp.astimezone(current.tzinfo)).total_seconds()
        if age < -30:
            effective = "unknown"
            reason = "timestamp_in_future"
        elif age > stale_after_seconds:
            effective = "unknown"
            reason = "stale_signal"
        else:
            effective = state
            reason = "reported_state"
        results.append({
            "id": check_id,
            "status": effective,
            "reason": reason,
            "age_seconds": max(0, int(age)),
        })

    overall = max((item["status"] for item in results), key=lambda status: SEVERITY[status], default="unknown")
    counts = {state: sum(item["status"] == state for item in results) for state in VALID_STATES}
    incidents = [
        {"check_id": item["id"], "severity": item["status"], "reason": item["reason"]}
        for item in results if item["status"] in {"degraded", "unavailable", "unknown"}
    ]
    return {
        "overall_status": overall,
        "checked_at": current.isoformat(),
        "check_count": len(results),
        "counts": counts,
        "checks": results,
        "incidents": incidents,
        "network_probes_performed": False,
        "automatic_remediation_performed": False,
        "sensitive_details_included": False,
    }
