"""Délégation interne de tâches : propositions contrôlées, sans affectation réelle."""
from __future__ import annotations

import re
from typing import Any

from .audit import validate_event
from .identity_security import validate_identity_registry

DELEGATION_PERMISSION = "delegate_internal_tasks"
ACTIVE = {"active", "deployed"}
PRIORITIES = {"low", "normal", "high", "urgent"}
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,119}$")
_EMAIL = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d .()/-]{7,}\d)(?!\w)")


class TaskDelegationError(ValueError):
    """Proposition de délégation invalide ou non autorisée."""


def _maps(identity_document: dict[str, Any]):
    validate_identity_registry(identity_document)
    identities = {item["agent_id"]: item for item in identity_document["identities"]}
    return identities


def _safe_description(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise TaskDelegationError(f"{field} doit contenir entre 1 et {maximum} caractères.")
    if _EMAIL.search(value) or _PHONE.search(value):
        raise TaskDelegationError(f"{field} semble contenir une coordonnée personnelle.")
    return value.strip()


def build_delegation_candidate(
    *, delegator_id: str, assignee_id: str, delegation_id: str,
    task_id: str, title: str, instructions: str, priority: str,
    created_at: str, identity_document: dict[str, Any],
    agents: dict[str, dict[str, Any]], due_at: str | None = None,
    approval_required: bool = True,
) -> dict[str, Any]:
    """Prépare une proposition uniquement si délégant et destinataire sont autorisés."""
    identities = _maps(identity_document)
    delegator, assignee = identities.get(delegator_id), identities.get(assignee_id)
    registry_delegator, registry_assignee = agents.get(delegator_id), agents.get(assignee_id)
    if not all((delegator, assignee, registry_delegator, registry_assignee)):
        raise TaskDelegationError("Délégant ou agent destinataire absent des registres.")
    if delegator_id == assignee_id:
        raise TaskDelegationError("Un agent ne peut pas se déléguer une tâche à lui-même.")
    if delegator.get("status") not in ACTIVE or registry_delegator.get("status") not in ACTIVE:
        raise TaskDelegationError("Délégant non actif.")
    if assignee.get("status") not in ACTIVE or registry_assignee.get("status") not in ACTIVE:
        raise TaskDelegationError("Agent destinataire non actif.")
    if delegator.get("profile_state") != "complete" or assignee.get("profile_state") != "complete":
        raise TaskDelegationError("Les deux profils doivent être complets.")
    if DELEGATION_PERMISSION in delegator.get("prohibited_actions", []) or DELEGATION_PERMISSION not in delegator.get("permissions", []):
        raise TaskDelegationError("Permission delegate_internal_tasks absente ou interdite.")
    # Si un responsable direct est défini, seul celui-ci peut déléguer à cet agent.
    if assignee.get("manager_id") is not None and assignee.get("manager_id") != delegator_id:
        raise TaskDelegationError("Le délégant n'est pas le responsable hiérarchique direct du destinataire.")
    if not isinstance(delegation_id, str) or not _ID.fullmatch(delegation_id):
        raise TaskDelegationError("delegation_id invalide.")
    if not isinstance(task_id, str) or not _ID.fullmatch(task_id):
        raise TaskDelegationError("task_id invalide.")
    if priority not in PRIORITIES:
        raise TaskDelegationError("Priorité invalide.")
    if not isinstance(approval_required, bool):
        raise TaskDelegationError("approval_required doit être booléen.")
    clean_title = _safe_description(title, "title", 160)
    clean_instructions = _safe_description(instructions, "instructions", 500)
    if due_at is not None:
        if not isinstance(due_at, str) or not due_at.strip() or len(due_at) > 40:
            raise TaskDelegationError("due_at doit être une date ISO-8601 ou null.")
    details = {
        "delegation_id": delegation_id, "assignee_id": assignee_id,
        "task_id": task_id, "title": clean_title,
        "instructions": clean_instructions, "priority": priority,
        "due_at": due_at, "approval_required": approval_required,
    }
    event = {
        "event_id": f"DELEGATION-EVENT-{delegation_id}",
        "occurred_at": created_at, "actor": delegator_id,
        "action": "task.delegation.proposed",
        "entity_type": "task_delegation", "entity_id": delegation_id,
        "details": details,
    }
    try:
        validate_event(event)
    except ValueError as exc:
        raise TaskDelegationError(str(exc)) from exc
    return {
        "status": "proposal_candidate",
        "delegation": {
            "delegation_id": delegation_id, "delegator_id": delegator_id,
            **details, "created_at": created_at,
            "approval_status": "pending" if approval_required else "not_required",
        },
        "permission_checked": DELEGATION_PERMISSION,
        "hierarchy_checked": True,
        "runtime_identity_authenticated": False,
        "owner_approval_checked": False,
        "task_registry_modified": False,
        "assignee_notified": False,
        "worker_started": False,
        "read_only": True,
    }


def build_delegation_center(events: list[dict[str, Any]], identity_document: dict[str, Any]) -> dict[str, Any]:
    """Projette les propositions explicites du journal sans les convertir en affectations."""
    identities = _maps(identity_document)
    seen: set[str] = set()
    proposals: list[dict[str, Any]] = []
    rejected = 0
    for event in events:
        if not isinstance(event, dict) or event.get("action") != "task.delegation.proposed":
            continue
        try:
            validate_event(event)
            if event["entity_type"] != "task_delegation":
                raise TaskDelegationError("Type d'entité invalide.")
            d = event["details"]
            required = {"delegation_id", "assignee_id", "task_id", "title", "instructions", "priority", "due_at", "approval_required"}
            if set(d) != required:
                raise TaskDelegationError("Schéma de délégation invalide.")
            delegation_id, delegator_id, assignee_id = d["delegation_id"], event["actor"], d["assignee_id"]
            if not isinstance(delegation_id, str) or delegation_id in seen:
                raise TaskDelegationError("Identifiant de délégation dupliqué ou invalide.")
            delegator, assignee = identities.get(delegator_id), identities.get(assignee_id)
            if delegator is None or assignee is None:
                raise TaskDelegationError("Identité inconnue.")
            if delegator.get("status") not in ACTIVE or assignee.get("status") not in ACTIVE:
                raise TaskDelegationError("Identité inactive.")
            if delegator.get("profile_state") != "complete" or assignee.get("profile_state") != "complete":
                raise TaskDelegationError("Profil incomplet.")
            if DELEGATION_PERMISSION not in delegator.get("permissions", []):
                raise TaskDelegationError("Permission de délégation absente.")
            if assignee.get("manager_id") is not None and assignee.get("manager_id") != delegator_id:
                raise TaskDelegationError("Hiérarchie non respectée.")
            if d["priority"] not in PRIORITIES or not isinstance(d["approval_required"], bool):
                raise TaskDelegationError("Priorité ou exigence d'approbation invalide.")
            _safe_description(d["title"], "title", 160)
            _safe_description(d["instructions"], "instructions", 500)
            seen.add(delegation_id)
            proposals.append({
                "delegation_id": delegation_id, "delegator_id": delegator_id,
                **d, "created_at": event["occurred_at"],
                "status": "proposal_recorded_not_assigned",
            })
        except (ValueError, KeyError, TypeError):
            rejected += 1
    proposals.sort(key=lambda item: (item["created_at"], item["delegation_id"]))
    return {
        "status": "available" if proposals else "no_recorded_proposals",
        "proposals": proposals, "proposal_count": len(proposals),
        "rejected_events": rejected, "source": "explicit_append_only_audit_events",
        "task_assignments_executed": 0, "notifications_sent": 0,
        "read_only": True,
    }
