"""Centre de validation PAPI : registre consultatif et événements candidats, sans écriture."""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from .audit import AuditError, validate_event


class ApprovalCenterError(ValueError):
    """Demande ou transition d'approbation invalide."""


_REQUEST_ACTIONS = {"approval.requested"}
_DECISION_ACTIONS = {"approval.approved", "approval.rejected"}
_RISKS = {"low", "medium", "high", "critical"}
_SENSITIVE_WORDS = ("password", "passwd", "secret", "token", "otp", "pin", "cvv", "credential", "authorization")


def _timestamp(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ApprovalCenterError(f"{field} doit être une date ISO-8601.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApprovalCenterError(f"{field} invalide.") from exc
    if parsed.tzinfo is None:
        raise ApprovalCenterError(f"{field} doit inclure un fuseau horaire.")
    return value


def _safe_text(value: Any, field: str, maximum: int = 300) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ApprovalCenterError(f"{field} doit être un texte de 1 à {maximum} caractères.")
    lowered = value.casefold()
    if any(word in lowered for word in _SENSITIVE_WORDS):
        raise ApprovalCenterError(f"{field} contient un terme sensible interdit.")
    return value


def build_approval_center(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Projette les demandes et décisions d'approbation depuis les événements validés."""
    if not isinstance(events, list):
        raise ApprovalCenterError("events doit être une liste.")
    requests: dict[str, dict[str, Any]] = {}
    for event in events:
        try:
            validate_event(event)
        except (AuditError, TypeError) as exc:
            raise ApprovalCenterError("Événement d'audit invalide.") from exc
        action = event["action"]
        if action not in _REQUEST_ACTIONS | _DECISION_ACTIONS:
            continue
        if event["entity_type"] != "approval":
            raise ApprovalCenterError("Les événements approval.* doivent cibler entity_type=approval.")
        request_id = event["entity_id"]
        details = event["details"]
        if action == "approval.requested":
            if request_id in requests:
                raise ApprovalCenterError("Demande d'approbation dupliquée.")
            required = {"action_type", "description", "risk", "requested_by", "required_approver"}
            if set(details) != required:
                raise ApprovalCenterError("Détails de demande incomplets ou inattendus.")
            action_type = _safe_text(details["action_type"], "action_type", 80)
            description = _safe_text(details["description"], "description", 300)
            requested_by = _safe_text(details["requested_by"], "requested_by", 120)
            required_approver = _safe_text(details["required_approver"], "required_approver", 120)
            risk = details["risk"]
            if not isinstance(risk, str) or risk not in _RISKS:
                raise ApprovalCenterError("Niveau de risque invalide.")
            requests[request_id] = {
                "request_id": request_id, "action_type": action_type,
                "description": description, "risk": risk,
                "requested_by": requested_by, "required_approver": required_approver,
                "status": "pending", "requested_at": event["occurred_at"],
                "decision": None, "history": [{
                    "action": action, "occurred_at": event["occurred_at"],
                    "actor": event["actor"],
                }],
            }
            continue
        current = requests.get(request_id)
        if current is None:
            raise ApprovalCenterError("Décision pour une demande inexistante.")
        if current["status"] != "pending":
            raise ApprovalCenterError("Une demande ne peut recevoir qu'une seule décision.")
        if details:
            raise ApprovalCenterError("Une décision ne doit contenir aucun détail supplémentaire.")
        if event["actor"] != current["required_approver"]:
            raise ApprovalCenterError("Décision émise par un approbateur non autorisé.")
        decision = "approved" if action == "approval.approved" else "rejected"
        current["status"] = decision
        current["decision"] = decision
        current["decided_at"] = event["occurred_at"]
        current["history"].append({
            "action": action, "occurred_at": event["occurred_at"],
            "actor": event["actor"],
        })

    items = [requests[key] for key in sorted(requests)]
    return {
        "requests": items,
        "summary": {
            "total": len(items),
            "pending": sum(item["status"] == "pending" for item in items),
            "approved": sum(item["status"] == "approved" for item in items),
            "rejected": sum(item["status"] == "rejected" for item in items),
        },
        "source": "append_only_audit_events",
        "read_only": True,
        "writes_performed": 0,
        "actions_executed": 0,
    }


def build_approval_decision_candidate(
    request: dict[str, Any], *, decision: str, actor: str,
    owner_actor: str, occurred_at: str, decision_id: str,
) -> dict[str, Any]:
    """Prépare un événement de décision ; n'enregistre ni n'exécute la demande."""
    if not isinstance(request, dict):
        raise ApprovalCenterError("request doit être un objet.")
    request_id = request.get("request_id")
    if not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 120:
        raise ApprovalCenterError("request_id invalide.")
    if request.get("status") != "pending":
        raise ApprovalCenterError("Seule une demande en attente peut être décidée.")
    if decision not in {"approve", "reject"}:
        raise ApprovalCenterError("decision doit être approve ou reject.")
    if not isinstance(owner_actor, str) or not owner_actor or actor != owner_actor:
        raise ApprovalCenterError("Seul l'acteur propriétaire configuré peut décider.")
    _safe_text(actor, "actor", 120)
    _timestamp(occurred_at, "occurred_at")
    _safe_text(decision_id, "decision_id", 120)
    action = "approval.approved" if decision == "approve" else "approval.rejected"
    event = {
        "event_id": decision_id,
        "occurred_at": occurred_at,
        "actor": actor,
        "action": action,
        "entity_type": "approval",
        "entity_id": request_id,
        "details": {},
    }
    try:
        validate_event(event)
    except AuditError as exc:
        raise ApprovalCenterError("Événement de décision invalide.") from exc
    return {
        "status": "decision_candidate",
        "event": event,
        "request_id": request_id,
        "decision": "approved" if decision == "approve" else "rejected",
        "read_only": True,
        "writes_performed": 0,
        "actions_executed": 0,
    }
