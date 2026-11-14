"""Approbation Ed25519 locale liée à un paquet de synchronisation exact.

Vérifie l'authenticité et la portée; ne transporte, n'importe et n'exécute rien.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .identity_ed25519 import Ed25519IdentityError, sign_ed25519_request, verify_ed25519_request
from .sync_bundle import SyncBundleError, validate_sync_bundle


class SyncBundleApprovalError(PermissionError):
    """Approbation du paquet absente, invalide ou hors portée."""


def _parse_time(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise SyncBundleApprovalError("Horodatage d'approbation absent.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SyncBundleApprovalError("Horodatage d'approbation invalide.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SyncBundleApprovalError("L'horodatage doit inclure un fuseau.")
    return parsed.astimezone(timezone.utc)


def sign_sync_bundle_approval(*, owner_id: str, private_key_path: Path,
                              bundle: dict[str, Any], approval_id: str,
                              issued_at: str, expires_at: str,
                              nonce: str | None = None,
                              timestamp: int | None = None) -> dict[str, Any]:
    """Produit une attestation signée pour un paquet; clé privée locale uniquement."""
    try:
        validate_sync_bundle(bundle)
    except SyncBundleError as exc:
        raise SyncBundleApprovalError(str(exc)) from exc
    issued, expires = _parse_time(issued_at), _parse_time(expires_at)
    if expires <= issued:
        raise SyncBundleApprovalError("L'expiration doit suivre l'émission.")
    if not isinstance(approval_id, str) or not approval_id.strip():
        raise SyncBundleApprovalError("Identifiant d'approbation absent.")
    payload = {
        "scope": "papi.sync_bundle.import",
        "decision": "approved",
        "approval_id": approval_id,
        "issued_at": issued.isoformat().replace("+00:00", "Z"),
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
        "bundle_digest": bundle["bundle_digest"],
        "source_instance_id": bundle["source_instance_id"],
        "destination_instance_id": bundle["destination_instance_id"],
        "export_id": bundle["export_id"],
        "event_ids": [event["event_id"] for event in bundle["events"]],
    }
    try:
        return sign_ed25519_request(owner_id, payload, private_key_path,
                                    timestamp=timestamp, nonce=nonce)
    except Ed25519IdentityError as exc:
        raise SyncBundleApprovalError(str(exc)) from exc


def verify_sync_bundle_approval(*, envelope: dict[str, Any], bundle: dict[str, Any],
                                owner_id: str, registry_path: Path,
                                replay_db: Path, expected_destination: str,
                                now_epoch: int | None = None,
                                now: datetime | None = None,
                                max_approval_ttl_seconds: int = 900,
                                consume_nonce: bool = True) -> dict[str, Any]:
    """Vérifie signature, propriétaire, destination, digest, événements et anti-rejeu."""
    try:
        validate_sync_bundle(bundle, expected_destination=expected_destination)
        verified = verify_ed25519_request(envelope, registry_path=registry_path,
                                           replay_db=replay_db, now=now_epoch,
                                           consume_nonce=consume_nonce)
    except (SyncBundleError, Ed25519IdentityError) as exc:
        raise SyncBundleApprovalError(str(exc)) from exc
    if verified["agent_id"] != owner_id:
        raise SyncBundleApprovalError("Seul le propriétaire désigné peut approuver ce paquet.")
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise SyncBundleApprovalError("Attestation absente.")
    expected = {
        "scope": "papi.sync_bundle.import",
        "decision": "approved",
        "bundle_digest": bundle["bundle_digest"],
        "source_instance_id": bundle["source_instance_id"],
        "destination_instance_id": bundle["destination_instance_id"],
        "export_id": bundle["export_id"],
        "event_ids": [event["event_id"] for event in bundle["events"]],
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        raise SyncBundleApprovalError("L'approbation ne correspond pas exactement au paquet.")
    if not isinstance(payload.get("approval_id"), str) or not payload["approval_id"].strip():
        raise SyncBundleApprovalError("Identifiant d'approbation invalide.")
    issued, expires = _parse_time(payload.get("issued_at")), _parse_time(payload.get("expires_at"))
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise SyncBundleApprovalError("L'horloge de vérification doit inclure un fuseau.")
    current = current.astimezone(timezone.utc)
    ttl = (expires - issued).total_seconds()
    if ttl <= 0 or ttl > max_approval_ttl_seconds or current < issued or current >= expires:
        raise SyncBundleApprovalError("Approbation expirée, future ou durée excessive.")
    return {
        "authenticated": True,
        "owner_id": owner_id,
        "approval_id": payload["approval_id"],
        "bundle_digest": bundle["bundle_digest"],
        "destination_instance_id": expected_destination,
        "event_count": len(bundle["events"]),
        "signature_verified": True,
        "nonce_replay_protected": bool(consume_nonce),
        "nonce_consumed": bool(verified.get("nonce_consumed", False)),
        "execution_enabled": False,
        "import_performed": False,
        "durable_consumption_required": True,
    }
