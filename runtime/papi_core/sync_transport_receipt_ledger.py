"""Registre SQLite local des reçus de transport vérifiés."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from .sync_transport_receipt import (
    SyncTransportReceiptError,
    verify_sync_transport_receipt,
)


class SyncTransportReceiptLedgerError(ValueError):
    """Conflit ou erreur d'intégrité du registre des reçus de transport."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as exc:
        raise SyncTransportReceiptLedgerError("Reçu non canonique.") from exc


_SCHEMA = """
CREATE TABLE IF NOT EXISTS sync_transport_receipts (
    receipt_id TEXT PRIMARY KEY,
    delivery_id TEXT NOT NULL UNIQUE,
    request_body_sha256 TEXT NOT NULL,
    source_instance_id TEXT NOT NULL,
    destination_instance_id TEXT NOT NULL,
    receipt_sha256 TEXT NOT NULL UNIQUE,
    receipt_json TEXT NOT NULL,
    verified_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    status TEXT NOT NULL CHECK(status = 'verified_transport_receipt')
);
"""


def record_verified_sync_transport_receipt(
    *, request: object, receipt: object, registry_path: Path,
    replay_db: Path, ledger_db: Path, now: int | None = None,
) -> dict[str, Any]:
    """Vérifie, consomme le nonce et archive le reçu dans UNE transaction SQLite.

    replay_db et ledger_db doivent désigner le même fichier : la réservation
    anti-rejeu et l'insertion métier sont alors validées ou annulées ensemble.
    Aucun réseau, import ou déclenchement d'exécution n'est effectué.
    """
    if Path(replay_db).resolve() != Path(ledger_db).resolve():
        raise SyncTransportReceiptLedgerError(
            "Le registre anti-rejeu et le registre des reçus doivent partager la même base SQLite."
        )
    if not isinstance(receipt, dict) or not isinstance(receipt.get("payload"), dict):
        raise SyncTransportReceiptLedgerError("Enveloppe de reçu absente.")
    payload = receipt["payload"]
    receipt_id, delivery_id = payload.get("receipt_id"), payload.get("delivery_id")
    receipt_json = _canonical(receipt).decode("utf-8")
    receipt_digest = hashlib.sha256(receipt_json.encode("utf-8")).hexdigest()
    if not isinstance(receipt_id, str) or not receipt_id.strip() or not isinstance(delivery_id, str):
        raise SyncTransportReceiptLedgerError("Identifiants du reçu invalides.")

    path = Path(ledger_db)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        with sqlite3.connect(path, timeout=30, isolation_level=None) as db:
            db.execute("PRAGMA busy_timeout=30000")
            db.executescript(_SCHEMA)
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT receipt_id, delivery_id, receipt_sha256 FROM sync_transport_receipts "
                "WHERE receipt_id=? OR delivery_id=?", (receipt_id, delivery_id)
            ).fetchone()
            if existing:
                if existing == (receipt_id, delivery_id, receipt_digest):
                    db.execute("ROLLBACK")
                    return {
                        "status": "already_recorded", "receipt_id": receipt_id,
                        "delivery_id": delivery_id, "receipt_sha256": receipt_digest,
                        "receipt_committed": True, "network_transfer_performed": False,
                        "import_performed": False, "execution_enabled": False,
                    }
                raise SyncTransportReceiptLedgerError(
                    "Identifiant de reçu ou livraison déjà associé à une autre preuve."
                )

            verified = verify_sync_transport_receipt(
                request=request, receipt=receipt, registry_path=Path(registry_path),
                replay_db=path, now=now, replay_connection=db,
            )
            db.execute(
                "INSERT INTO sync_transport_receipts "
                "(receipt_id,delivery_id,request_body_sha256,source_instance_id,"
                "destination_instance_id,receipt_sha256,receipt_json,status) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (receipt_id, delivery_id, verified["request_body_sha256"],
                 verified["source_instance_id"], verified["destination_instance_id"],
                 receipt_digest, receipt_json, "verified_transport_receipt"),
            )
            db.execute("COMMIT")
    except SyncTransportReceiptLedgerError:
        raise
    except SyncTransportReceiptError as exc:
        raise SyncTransportReceiptLedgerError(str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise SyncTransportReceiptLedgerError(
            "Conflit ou rejeu concurrent; nonce et reçu annulés atomiquement."
        ) from exc
    except sqlite3.Error as exc:
        raise SyncTransportReceiptLedgerError("Échec SQLite; nonce et reçu annulés.") from exc

    os.chmod(path, 0o600)
    return {
        "status": "recorded", "receipt_id": receipt_id, "delivery_id": delivery_id,
        "receipt_sha256": receipt_digest,
        "destination_signature_verified": verified["destination_signature_verified"],
        "destination_nonce_consumed": verified["destination_nonce_consumed"],
        "receipt_committed": True, "network_transfer_performed": False,
        "import_performed": False, "execution_enabled": False,
        "manual_reconciliation_required": False,
        "nonce_and_receipt_atomic": True,
    }
