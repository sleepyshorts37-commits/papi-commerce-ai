"""Centre d'incidents PAPI construit depuis le journal append-only."""
from __future__ import annotations

from typing import Any

from .audit import AuditError, validate_event


class IncidentCenterError(ValueError):
    """Événement d'incident incohérent."""


_SEVERITIES = {"info", "warning", "critical"}
_CATEGORIES = {"worker", "job", "security", "platform", "data", "integration", "other"}
_ACTIONS = {"incident.reported", "incident.acknowledged", "incident.resolved"}


def build_incident_center(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Projette les événements d'incident en état courant, sans écrire dans le journal."""
    if not isinstance(events, list):
        raise IncidentCenterError("events doit être une liste.")
    incidents: dict[str, dict[str, Any]] = {}
    for event in events:
        try:
            validate_event(event)
        except (AuditError, TypeError) as exc:
            raise IncidentCenterError("Événement d'audit invalide.") from exc
        action = event["action"]
        if action not in _ACTIONS:
            continue
        incident_id = event["entity_id"]
        details = event["details"]
        if event["entity_type"] != "incident":
            raise IncidentCenterError("Les événements incident.* doivent cibler entity_type=incident.")
        if action == "incident.reported":
            if incident_id in incidents:
                raise IncidentCenterError("Un incident ne peut être déclaré deux fois.")
            severity, category = details.get("severity"), details.get("category")
            summary, recommendation = details.get("summary"), details.get("recommendation")
            if severity not in _SEVERITIES or category not in _CATEGORIES:
                raise IncidentCenterError("Gravité ou catégorie d'incident invalide.")
            if not isinstance(summary, str) or not summary.strip() or len(summary) > 300:
                raise IncidentCenterError("summary doit contenir 1 à 300 caractères.")
            if not isinstance(recommendation, str) or not recommendation.strip() or len(recommendation) > 500:
                raise IncidentCenterError("recommendation doit contenir 1 à 500 caractères.")
            incidents[incident_id] = {
                "incident_id": incident_id, "severity": severity, "category": category,
                "summary": summary, "recommendation": recommendation,
                "status": "open", "reported_at": event["occurred_at"],
                "last_updated_at": event["occurred_at"], "reported_by": event["actor"],
                "history": [{"action": action, "occurred_at": event["occurred_at"],
                             "actor": event["actor"]}],
            }
            continue
        current = incidents.get(incident_id)
        if current is None:
            raise IncidentCenterError("Transition d'un incident non déclaré.")
        if current["status"] not in ({"open"} if action == "incident.acknowledged" else {"open", "acknowledged"}):
            raise IncidentCenterError("Transition interdite depuis un incident non ouvert.")
        if details:
            raise IncidentCenterError("Les transitions incident ne doivent contenir aucun détail.")
        new_status = "acknowledged" if action == "incident.acknowledged" else "resolved"
        current["status"] = new_status
        current["last_updated_at"] = event["occurred_at"]
        current["history"].append({"action": action, "occurred_at": event["occurred_at"],
                                   "actor": event["actor"]})

    items = [incidents[key] for key in sorted(incidents)]
    counts = {status: sum(1 for item in items if item["status"] == status)
              for status in ("open", "acknowledged", "resolved")}
    severity_counts = {severity: sum(1 for item in items
                                     if item["severity"] == severity and item["status"] != "resolved")
                       for severity in ("info", "warning", "critical")}
    return {
        "incidents": items,
        "summary": {"total": len(items), "by_status": counts,
                    "active_by_severity": severity_counts},
        "source": "append_only_audit_events",
        "read_only": True,
        "writes_performed": 0,
        "notifications_sent": 0,
        "external_actions_performed": 0,
    }
