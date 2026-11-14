"""Checkpoints Ed25519 des registres locaux de reçus de transport."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from .identity_ed25519 import (
    Ed25519IdentityError,
    sign_ed25519_request,
    verify_ed25519_request,
)
from .sync_transport_receipt_ledger import (
    SyncTransportReceiptLedgerError,
    audit_sync_transport_receipt_ledger,
)


class SyncTransportReceiptCheckpointError(ValueError):
    """Checkpoint de registre absent, invalide ou devenu obsolète."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as exc:
        raise SyncTransportReceiptCheckpointError("Contenu du checkpoint non canonique.") from exc


def _ledger_snapshot(ledger_db: Path) -> dict[str, Any]:
    path = Path(ledger_db)
    if not path.is_file():
        raise SyncTransportReceiptCheckpointError("Registre des reçus introuvable.")
    try:
        uri = f"file:{path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=10) as db:
            rows = db.execute(
                "SELECT receipt_id, delivery_id, request_body_sha256, source_instance_id, "
                "destination_instance_id, receipt_sha256, receipt_json, verified_at, status "
                "FROM sync_transport_receipts ORDER BY receipt_id"
            ).fetchall()
    except sqlite3.Error as exc:
        raise SyncTransportReceiptCheckpointError("Lecture du registre impossible.") from exc
    records = [list(row) for row in rows]
    return {
        "records_count": len(records),
        "ledger_sha256": hashlib.sha256(_canonical(records)).hexdigest(),
    }


def create_sync_transport_receipt_checkpoint(
    *, ledger_db: Path, agent_id: str, private_key_path: Path,
    key_version: int = 1, timestamp: int | None = None,
) -> dict[str, Any]:
    """Crée un checkpoint signé sans modifier le registre ni consommer de nonce."""
    try:
        audit = audit_sync_transport_receipt_ledger(ledger_db=ledger_db)
        snapshot = _ledger_snapshot(ledger_db)
        if audit["records_audited"] != snapshot["records_count"]:
            raise SyncTransportReceiptCheckpointError("Comptage du registre incohérent.")
        payload = {
            "protocol": "papi.sync.transport-receipt-checkpoint",
            "protocol_version": 1,
            **snapshot,
            "audit_status": audit["status"],
        }
        envelope = sign_ed25519_request(
            agent_id, payload, Path(private_key_path),
            key_version=key_version, timestamp=timestamp,
        )
    except (SyncTransportReceiptLedgerError, Ed25519IdentityError) as exc:
        raise SyncTransportReceiptCheckpointError("Création du checkpoint impossible.") from exc
    return {
        "schema_version": 1,
        "envelope": envelope,
        "network_transfer_performed": False,
        "ledger_modified": False,
        "nonce_consumed": False,
    }


def verify_sync_transport_receipt_checkpoint(
    *, checkpoint: object, ledger_db: Path, registry_path: Path,
    now: int | None = None,
) -> dict[str, Any]:
    """Vérifie la signature Ed25519 et compare le checkpoint au registre actuel."""
    if not isinstance(checkpoint, dict) or set(checkpoint) != {
        "schema_version", "envelope", "network_transfer_performed",
        "ledger_modified", "nonce_consumed",
    }:
        raise SyncTransportReceiptCheckpointError("Structure du checkpoint invalide.")
    if (checkpoint["schema_version"] != 1
            or checkpoint["network_transfer_performed"] is not False
            or checkpoint["ledger_modified"] is not False
            or checkpoint["nonce_consumed"] is not False):
        raise SyncTransportReceiptCheckpointError("Métadonnées du checkpoint invalides.")
    envelope = checkpoint["envelope"]
    if not isinstance(envelope, dict) or not isinstance(envelope.get("payload"), dict):
        raise SyncTransportReceiptCheckpointError("Enveloppe signée absente.")
    payload = envelope["payload"]
    required = {
        "protocol", "protocol_version", "records_count", "ledger_sha256", "audit_status",
    }
    if (set(payload) != required
            or payload.get("protocol") != "papi.sync.transport-receipt-checkpoint"
            or payload.get("protocol_version") != 1
            or payload.get("audit_status") != "integrity_verified"
            or not isinstance(payload.get("records_count"), int)
            or isinstance(payload.get("records_count"), bool)
            or payload["records_count"] < 0
            or not isinstance(payload.get("ledger_sha256"), str)
            or len(payload["ledger_sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in payload["ledger_sha256"])):
        raise SyncTransportReceiptCheckpointError("Contenu signé du checkpoint invalide.")
    try:
        signature = verify_ed25519_request(
            envelope, registry_path=Path(registry_path), replay_db=Path("."),
            now=now, consume_nonce=False,
        )
        audit = audit_sync_transport_receipt_ledger(ledger_db=ledger_db)
        current = _ledger_snapshot(ledger_db)
    except (Ed25519IdentityError, SyncTransportReceiptLedgerError) as exc:
        raise SyncTransportReceiptCheckpointError("Signature ou audit du registre invalide.") from exc
    if (audit["status"] != "integrity_verified"
            or current != {
                "records_count": payload["records_count"],
                "ledger_sha256": payload["ledger_sha256"],
            }):
        raise SyncTransportReceiptCheckpointError(
            "Le registre a changé depuis la création du checkpoint."
        )
    return {
        "status": "checkpoint_verified",
        "agent_id": signature["agent_id"],
        "records_count": current["records_count"],
        "ledger_sha256": current["ledger_sha256"],
        "signature_verified": True,
        "nonce_consumed": False,
        "network_transfer_performed": False,
    }
