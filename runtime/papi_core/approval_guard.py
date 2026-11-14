"""Contrôle d'approbation humaine, explicite, limitée et anti-rejeu.

Ce module valide une attestation fournie par une couche d'identité de confiance.
Il ne vérifie pas lui-même l'identité du propriétaire et ne persiste aucun nonce.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


class ApprovalDenied(RuntimeError):
    """Approbation absente, invalide, expirée ou déjà consommée."""


_REQUIRED = {
    "approval_id",
    "task_id",
    "handler",
    "action_class",
    "decision",
    "approved_by",
    "approved_at",
    "expires_at",
}


def _utc_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ApprovalDenied(f"Champ d'approbation invalide : {field}.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApprovalDenied(f"Horodatage d'approbation invalide : {field}.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ApprovalDenied(f"Fuseau horaire obligatoire : {field}.")
    return parsed.astimezone(timezone.utc)


def authorize_scoped_approval(
    *,
    approval: dict[str, Any],
    task: dict[str, Any],
    handler: str,
    action_class: str,
    policy: dict[str, Any],
    consumed_approval_ids: set[str] | list[str] | tuple[str, ...] = (),
    now: datetime | None = None,
) -> dict[str, str]:
    """Valide une approbation propriétaire liée à une seule tâche et action.

    L'appelant doit fournir une attestation issue d'une session propriétaire
    authentifiée. Les IDs consommés doivent provenir d'un stockage atomique
    durable ; cette fonction seule ne garantit pas l'anti-rejeu concurrent.
    """
    if not all(isinstance(item, dict) for item in (approval, task, policy)):
        raise ApprovalDenied("Approbation, tâche et politique doivent être des objets.")
    if not _REQUIRED.issubset(approval):
        raise ApprovalDenied("Attestation d'approbation incomplète.")
    if not all(isinstance(approval.get(key), str) and approval[key].strip()
               for key in _REQUIRED):
        raise ApprovalDenied("Attestation d'approbation invalide.")
    if approval["decision"] != "approved":
        raise ApprovalDenied("La décision humaine n'est pas une approbation.")
    if approval["approved_by"] != policy.get("owner_id"):
        raise ApprovalDenied("Seul le propriétaire désigné peut approuver cette action.")
    if approval["task_id"] != task.get("task_id"):
        raise ApprovalDenied("Approbation liée à une autre tâche.")
    if approval["handler"] != handler or approval["action_class"] != action_class:
        raise ApprovalDenied("Approbation liée à une autre action.")
    if task.get("status") != "in_progress":
        raise ApprovalDenied("La tâche n'est pas autorisée à être exécutée.")
    approval_id = approval["approval_id"]
    if approval_id in consumed_approval_ids:
        raise ApprovalDenied("Cette approbation a déjà été consommée.")

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ApprovalDenied("L'horloge de validation doit être timezone-aware.")
    current = current.astimezone(timezone.utc)
    approved_at = _utc_datetime(approval["approved_at"], "approved_at")
    expires_at = _utc_datetime(approval["expires_at"], "expires_at")
    max_ttl = policy.get("max_approval_ttl_seconds", 900)
    if isinstance(max_ttl, bool) or not isinstance(max_ttl, int) or not 1 <= max_ttl <= 86400:
        raise ApprovalDenied("Durée maximale d'approbation invalide.")
    if approved_at > current + timedelta(seconds=60):
        raise ApprovalDenied("L'approbation est datée dans le futur.")
    if expires_at <= current:
        raise ApprovalDenied("L'approbation a expiré.")
    if expires_at <= approved_at or expires_at - approved_at > timedelta(seconds=max_ttl):
        raise ApprovalDenied("Durée de validité de l'approbation hors limites.")

    return {
        "approval_id": approval_id,
        "task_id": approval["task_id"],
        "handler": handler,
        "action_class": action_class,
        "approved_by": approval["approved_by"],
        "decision": "approved",
    }
