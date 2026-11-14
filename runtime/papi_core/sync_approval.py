"""Approbation Ed25519 liée au digest exact d'un plan de synchronisation.

La vérification cryptographique authentifie le propriétaire via le registre de clés.
La consommation durable et atomique doit ensuite être faite par la RPC SQL dédiée.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .approval_guard import ApprovalDenied, authorize_scoped_approval
from .identity_ed25519 import Ed25519IdentityError, verify_ed25519_request
from .sync_protocol import SyncProtocolError, validate_plan_integrity


class SyncApprovalError(PermissionError):
    """Approbation du plan invalide ou non liée au plan exact."""


def verify_sync_plan_approval(
    *,
    envelope: dict[str, Any],
    plan: dict[str, Any],
    task: dict[str, Any],
    policy: dict[str, Any],
    registry_path,
    replay_db,
    now_epoch: int | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Vérifie une signature propriétaire Ed25519 et sa portée exacte.

    Cette fonction ne consomme pas le registre SQL d'approbation et n'exécute
    aucune action. Le backend doit appeler papi_consume_sync_approval ensuite.
    """
    try:
        validate_plan_integrity(plan)
        verified = verify_ed25519_request(
            envelope, registry_path=registry_path, replay_db=replay_db, now=now_epoch
        )
    except (SyncProtocolError, Ed25519IdentityError) as exc:
        raise SyncApprovalError(str(exc)) from exc

    payload = envelope.get("payload") if isinstance(envelope, dict) else None
    if not isinstance(payload, dict):
        raise SyncApprovalError("Payload d'approbation absent.")
    if verified["agent_id"] != policy.get("owner_id"):
        raise SyncApprovalError("La signature ne provient pas du propriétaire désigné.")

    expected_ids = [action["action_id"] for action in plan["actions"]]
    expected = {
        "plan_digest": plan["plan_digest"],
        "destination_instance": plan["destination_instance"],
        "action_ids": expected_ids,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        raise SyncApprovalError("L'approbation ne correspond pas exactement au plan.")
    approval_fields = (
        "approval_id", "task_id", "handler", "action_class",
        "decision", "approved_by", "approved_at", "expires_at",
    )
    if any(not isinstance(payload.get(key), str) or not payload[key].strip()
           for key in approval_fields):
        raise SyncApprovalError("Attestation d'approbation incomplète.")
    if payload["approved_by"] != verified["agent_id"]:
        raise SyncApprovalError("L'identité signataire et approbateur diffèrent.")

    try:
        scoped = authorize_scoped_approval(
            approval={key: payload[key] for key in approval_fields},
            task=task,
            handler=payload["handler"],
            action_class=payload["action_class"],
            policy=policy,
            consumed_approval_ids=(),
            now=now or datetime.now(timezone.utc),
        )
    except ApprovalDenied as exc:
        raise SyncApprovalError(str(exc)) from exc

    return {
        **scoped,
        "plan_digest": expected["plan_digest"],
        "destination_instance": expected["destination_instance"],
        "action_ids": expected_ids,
        "signature_verified": True,
        "nonce_replay_protected": True,
        "durable_consumption_required": True,
        "execution_enabled": False,
        "writes_performed": False,
    }
