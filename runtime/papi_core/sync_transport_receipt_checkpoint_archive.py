"""Archive SQLite local et append-only des checkpoints signés des reçus."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from .identity_ed25519 import Ed25519IdentityError, verify_ed25519_archived_signature
from .sync_transport_receipt_checkpoint import (
    SyncTransportReceiptCheckpointError,
    verify_sync_transport_receipt_checkpoint,
)


class SyncTransportReceiptCheckpointArchiveError(ValueError):
    """Erreur d'archivage, de collision ou d'intégrité des checkpoints."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as exc:
        raise SyncTransportReceiptCheckpointArchiveError(
            "Checkpoint non canonique."
        ) from exc


_SCHEMA = """
CREATE TABLE IF NOT EXISTS sync_transport_receipt_checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    checkpoint_sha256 TEXT NOT NULL UNIQUE,
    checkpoint_json TEXT NOT NULL,
    archived_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TRIGGER IF NOT EXISTS sync_transport_receipt_checkpoints_no_update
BEFORE UPDATE ON sync_transport_receipt_checkpoints
BEGIN
    SELECT RAISE(ABORT, 'checkpoint archive is append-only');
END;
CREATE TRIGGER IF NOT EXISTS sync_transport_receipt_checkpoints_no_delete
BEFORE DELETE ON sync_transport_receipt_checkpoints
BEGIN
    SELECT RAISE(ABORT, 'checkpoint archive is append-only');
END;
"""


def _initialize(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        with sqlite3.connect(path, timeout=30) as db:
            db.execute("PRAGMA busy_timeout=30000")
            db.executescript(_SCHEMA)
        os.chmod(path, 0o600)
    except (OSError, sqlite3.Error) as exc:
        raise SyncTransportReceiptCheckpointArchiveError(
            "Initialisation de l'archive impossible."
        ) from exc


def archive_sync_transport_receipt_checkpoint(
    *, checkpoint: object, archive_db: Path, ledger_db: Path,
    registry_path: Path, now: int | None = None,
) -> dict[str, Any]:
    """Vérifie un checkpoint courant puis l'archive sans modifier le ledger."""
    try:
        verification = verify_sync_transport_receipt_checkpoint(
            checkpoint=checkpoint, ledger_db=Path(ledger_db),
            registry_path=Path(registry_path), now=now,
        )
    except SyncTransportReceiptCheckpointError as exc:
        raise SyncTransportReceiptCheckpointArchiveError(
            "Le checkpoint doit être valide pour le registre courant avant archivage."
        ) from exc
    encoded = _canonical(checkpoint).decode("utf-8")
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    path = Path(archive_db)
    _initialize(path)
    try:
        with sqlite3.connect(path, timeout=30, isolation_level=None) as db:
            db.execute("PRAGMA busy_timeout=30000")
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT checkpoint_sha256, checkpoint_json "
                "FROM sync_transport_receipt_checkpoints WHERE checkpoint_id=?",
                (digest,),
            ).fetchone()
            if existing:
                if existing == (digest, encoded):
                    db.execute("ROLLBACK")
                    return {
                        "status": "already_archived", "checkpoint_id": digest,
                        "checkpoint_sha256": digest,
                        "records_count": verification["records_count"],
                        "archive_modified": False,
                    }
                raise SyncTransportReceiptCheckpointArchiveError(
                    "Collision ou contenu divergent pour cet identifiant."
                )
            db.execute(
                "INSERT INTO sync_transport_receipt_checkpoints "
                "(checkpoint_id, checkpoint_sha256, checkpoint_json) VALUES (?,?,?)",
                (digest, digest, encoded),
            )
            db.execute("COMMIT")
    except SyncTransportReceiptCheckpointArchiveError:
        raise
    except sqlite3.Error as exc:
        raise SyncTransportReceiptCheckpointArchiveError(
            "Écriture atomique dans l'archive impossible."
        ) from exc
    return {
        "status": "archived", "checkpoint_id": digest,
        "checkpoint_sha256": digest,
        "records_count": verification["records_count"],
        "archive_modified": True,
    }


def audit_sync_transport_receipt_checkpoint_archive(
    *, archive_db: Path, registry_path: Path, now: int | None = None,
) -> dict[str, Any]:
    """Audite en lecture seule les digests, le JSON canonique et les signatures."""
    path = Path(archive_db)
    if not path.is_file():
        raise SyncTransportReceiptCheckpointArchiveError("Archive introuvable.")
    try:
        uri = f"file:{path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=10) as db:
            rows = db.execute(
                "SELECT checkpoint_id, checkpoint_sha256, checkpoint_json "
                "FROM sync_transport_receipt_checkpoints ORDER BY checkpoint_id"
            ).fetchall()
    except sqlite3.Error as exc:
        raise SyncTransportReceiptCheckpointArchiveError(
            "Lecture de l'archive impossible."
        ) from exc

    audited = 0
    for checkpoint_id, expected_digest, checkpoint_json in rows:
        try:
            checkpoint = json.loads(checkpoint_json)
            canonical = _canonical(checkpoint)
            digest = hashlib.sha256(canonical).hexdigest()
            if (canonical.decode("utf-8") != checkpoint_json
                    or digest != expected_digest or digest != checkpoint_id):
                raise SyncTransportReceiptCheckpointArchiveError(
                    f"Intégrité du checkpoint compromise : {checkpoint_id}."
                )
            if (not isinstance(checkpoint, dict)
                    or checkpoint.get("schema_version") != 1
                    or checkpoint.get("network_transfer_performed") is not False
                    or checkpoint.get("ledger_modified") is not False
                    or checkpoint.get("nonce_consumed") is not False):
                raise SyncTransportReceiptCheckpointArchiveError(
                    f"Métadonnées invalides : {checkpoint_id}."
                )
            envelope = checkpoint.get("envelope")
            if not isinstance(envelope, dict) or not isinstance(envelope.get("payload"), dict):
                raise SyncTransportReceiptCheckpointArchiveError(
                    f"Enveloppe absente : {checkpoint_id}."
                )
            payload = envelope["payload"]
            if (payload.get("protocol") != "papi.sync.transport-receipt-checkpoint"
                    or payload.get("protocol_version") != 1
                    or payload.get("audit_status") != "integrity_verified"):
                raise SyncTransportReceiptCheckpointArchiveError(
                    f"Protocole de checkpoint invalide : {checkpoint_id}."
                )
            historical = verify_ed25519_archived_signature(
                envelope, registry_path=Path(registry_path),
            )
            if historical["authorization_granted"] or historical["nonce_consumed"]:
                raise SyncTransportReceiptCheckpointArchiveError(
                    "Une vérification historique ne peut autoriser une action ni consommer un nonce."
                )
        except (ValueError, TypeError, KeyError, Ed25519IdentityError) as exc:
            if isinstance(exc, SyncTransportReceiptCheckpointArchiveError):
                raise
            raise SyncTransportReceiptCheckpointArchiveError(
                f"Signature ou contenu invalide : {checkpoint_id}."
            ) from exc
        audited += 1
    return {
        "status": "archive_integrity_verified",
        "records_audited": audited,
        "read_only": True,
        "signatures_verified": True,
        "nonce_consumed": False,
    }
