"""Machine à états déterministe pour le cycle de vie des tâches."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .audit import new_event
from .registry import VALID_STATUSES

TRANSITIONS = {
    "backlog": {"ready", "cancelled"},
    "ready": {"in_progress", "blocked", "cancelled"},
    "in_progress": {"blocked", "review", "cancelled"},
    "blocked": {"ready", "cancelled"},
    "review": {"in_progress", "blocked", "done"},
    "done": set(),
    "cancelled": set(),
}


class TransitionError(ValueError):
    """Transition interdite ou condition de clôture non satisfaite."""


def transition_task(
    task: dict[str, Any],
    new_status: str,
    *,
    actor: str,
    reason: str = "",
    evidence: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Retourne une copie mise à jour et son événement d'audit, sans écrire sur disque."""
    if not isinstance(task, dict):
        raise TransitionError("La tâche doit être un objet.")
    old_status = task.get("status")
    if old_status not in VALID_STATUSES or new_status not in VALID_STATUSES:
        raise TransitionError("Statut source ou destination invalide.")
    if new_status not in TRANSITIONS[old_status]:
        raise TransitionError(f"Transition interdite: {old_status} -> {new_status}.")
    if not isinstance(actor, str) or not actor.strip():
        raise TransitionError("Un acteur doit être identifié.")
    if new_status == "in_progress" and task.get("approval_required") is True:
        if task.get("approval_status") != "approved":
            raise TransitionError("Approbation du propriétaire requise avant exécution.")
    updated = deepcopy(task)
    if evidence is not None:
        if not isinstance(evidence, list) or not all(isinstance(item, str) and item.strip() for item in evidence):
            raise TransitionError("Les preuves doivent être une liste de références textuelles non vides.")
        updated["evidence"] = list(evidence)
    if new_status == "done":
        if old_status != "review":
            raise TransitionError("Une tâche doit passer par le contrôle qualité avant clôture.")
        if not updated.get("evidence") and not updated.get("result_url"):
            raise TransitionError("Une preuve ou un lien de résultat est obligatoire pour clôturer.")
    updated["status"] = new_status
    updated["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    event = new_event(
        event_id=f"EVT-{uuid4().hex.upper()}",
        actor=actor,
        action="task.status_changed",
        entity_type="task",
        entity_id=str(task.get("id", "unknown")),
        details={
            "from_status": old_status,
            "to_status": new_status,
            "reason": reason[:500],
            "evidence_count": len(updated.get("evidence", [])),
        },
    )
    return updated, event


def approve_task(task: dict[str, Any], *, approver: str, decision: str, reason: str = "") -> tuple[dict[str, Any], dict[str, Any]]:
    """Enregistre une décision explicite d'approbation ; ne déclenche aucune exécution."""
    if not isinstance(task, dict) or task.get("approval_required") is not True:
        raise TransitionError("Cette tâche ne demande pas d'approbation.")
    if not isinstance(approver, str) or not approver.strip():
        raise TransitionError("L'identité de l'approbateur est obligatoire.")
    if decision not in {"approved", "rejected"}:
        raise TransitionError("La décision doit être approved ou rejected.")
    if task.get("approval_status") in {"approved", "rejected"}:
        raise TransitionError("Une décision finale existe déjà ; créer une nouvelle demande pour la modifier.")
    updated = deepcopy(task)
    updated["approval_status"] = decision
    updated["approval_actor"] = approver
    updated["approval_reason"] = reason[:500]
    event = new_event(
        event_id=f"EVT-{uuid4().hex.upper()}",
        actor=approver,
        action=f"task.approval_{decision}",
        entity_type="task",
        entity_id=str(task.get("id", "unknown")),
        details={"decision": decision, "reason": reason[:500]},
    )
    return updated, event
