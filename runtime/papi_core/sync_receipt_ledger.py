"""Registre SQLite local de reçus vérifiés pour paquets PAPI sync."""
from __future__ import annotations
import os, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .sync_bundle_approval import SyncBundleApprovalError, verify_sync_bundle_approval

class SyncReceiptLedgerError(ValueError):
    """Reçu invalide ou conflit d'intégrité dans le registre local."""

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sync_bundle_receipts (
 bundle_digest TEXT PRIMARY KEY, approval_id TEXT NOT NULL UNIQUE,
 owner_id TEXT NOT NULL, source_instance_id TEXT NOT NULL,
 destination_instance_id TEXT NOT NULL, export_id TEXT NOT NULL,
 event_count INTEGER NOT NULL CHECK(event_count BETWEEN 0 AND 500),
 recorded_at TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status = 'verified_pending_manual_import')
);
CREATE TABLE IF NOT EXISTS sync_bundle_receipt_items (
 event_id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('memory','message')),
 record_id TEXT NOT NULL, content_digest TEXT NOT NULL, sequence INTEGER NOT NULL,
 bundle_digest TEXT NOT NULL REFERENCES sync_bundle_receipts(bundle_digest),
 UNIQUE(kind, record_id)
);
"""

def record_verified_sync_bundle(*, envelope: dict[str, Any], bundle: dict[str, Any],
    owner_id: str, registry_path: Path, replay_db: Path, ledger_db: Path,
    expected_destination: str, now_epoch: int | None = None,
    now: datetime | None = None, max_approval_ttl_seconds: int = 900) -> dict[str, Any]:
    """Vérifie une approbation puis inscrit reçu et références dans une transaction locale."""
    try:
        verified = verify_sync_bundle_approval(
            envelope=envelope, bundle=bundle, owner_id=owner_id,
            registry_path=registry_path, replay_db=replay_db,
            expected_destination=expected_destination, now_epoch=now_epoch,
            now=now, max_approval_ttl_seconds=max_approval_ttl_seconds)
    except SyncBundleApprovalError as exc:
        raise SyncReceiptLedgerError(str(exc)) from exc

    payload = envelope["payload"]
    recorded_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    ledger_db.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        with sqlite3.connect(ledger_db, timeout=30, isolation_level=None) as db:
            db.execute("PRAGMA busy_timeout=30000")
            db.execute("PRAGMA foreign_keys=ON")
            db.executescript(_SCHEMA)
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT approval_id, owner_id, source_instance_id, destination_instance_id, "
                "export_id, event_count FROM sync_bundle_receipts WHERE bundle_digest=?",
                (bundle["bundle_digest"],)).fetchone()
            if existing:
                expected = (owner_id, bundle["source_instance_id"],
                    bundle["destination_instance_id"], bundle["export_id"], len(bundle["events"]))
                if existing[1:] != expected:
                    raise SyncReceiptLedgerError("Digest déjà enregistré avec des métadonnées divergentes.")
                receipt_approval_id = existing[0]
                db.execute("COMMIT")
                status = "already_recorded"
            else:
                db.execute("INSERT INTO sync_bundle_receipts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (bundle["bundle_digest"], payload["approval_id"], owner_id,
                     bundle["source_instance_id"], bundle["destination_instance_id"],
                     bundle["export_id"], len(bundle["events"]), recorded_at,
                     "verified_pending_manual_import"))
                for event in bundle["events"]:
                    db.execute("INSERT INTO sync_bundle_receipt_items "
                        "(event_id,kind,record_id,content_digest,sequence,bundle_digest) "
                        "VALUES (?,?,?,?,?,?)",
                        (event["event_id"], event["kind"], event["record_id"],
                         event["content_digest"], event["sequence"], bundle["bundle_digest"]))
                receipt_approval_id = payload["approval_id"]
                db.execute("COMMIT")
                status = "recorded"
    except SyncReceiptLedgerError:
        raise
    except sqlite3.IntegrityError as exc:
        raise SyncReceiptLedgerError(
            "Conflit d'événement ou de ressource déjà référencé; transaction annulée.") from exc
    except sqlite3.Error as exc:
        raise SyncReceiptLedgerError("Échec SQLite; transaction annulée.") from exc

    os.chmod(ledger_db, 0o600)
    return {"status": status, "bundle_digest": bundle["bundle_digest"],
        "approval_id": receipt_approval_id, "latest_verified_approval_id": verified["approval_id"], "event_count": verified["event_count"],
        "receipt_committed": True, "import_performed": False,
        "execution_enabled": False, "ledger_scope": "single_instance_local"}
