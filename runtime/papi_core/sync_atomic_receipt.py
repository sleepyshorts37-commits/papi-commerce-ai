"""Consommation atomique du nonce Ed25519 et enregistrement du reçu local."""
from __future__ import annotations
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .sync_bundle_approval import SyncBundleApprovalError, verify_sync_bundle_approval
from .identity_ed25519 import MAX_CLOCK_SKEW_SECONDS

class AtomicSyncReceiptError(ValueError):
    """Approbation, anti-rejeu ou reçu invalide."""

_SCHEMA = """
CREATE TABLE IF NOT EXISTS used_nonces (
 agent_id TEXT NOT NULL, nonce TEXT NOT NULL, expires_at INTEGER NOT NULL,
 PRIMARY KEY(agent_id, nonce)
);
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

def commit_approved_sync_receipt(*, envelope: dict[str, Any], bundle: dict[str, Any],
    owner_id: str, registry_path: Path, ledger_db: Path, expected_destination: str,
    now_epoch: int | None = None, now: datetime | None = None,
    max_approval_ttl_seconds: int = 900) -> dict[str, Any]:
    """Vérifie cryptographiquement puis consomme le nonce et inscrit le reçu en une transaction SQLite."""
    try:
        verified = verify_sync_bundle_approval(
            envelope=envelope, bundle=bundle, owner_id=owner_id,
            registry_path=registry_path, replay_db=ledger_db,
            expected_destination=expected_destination, now_epoch=now_epoch,
            now=now, max_approval_ttl_seconds=max_approval_ttl_seconds,
            consume_nonce=False)
    except SyncBundleApprovalError as exc:
        raise AtomicSyncReceiptError(str(exc)) from exc

    issued = envelope["timestamp"]
    current_epoch = int(now_epoch if now_epoch is not None else datetime.now(timezone.utc).timestamp())
    nonce_expiry = issued + MAX_CLOCK_SKEW_SECONDS
    recorded_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    ledger_db.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        with sqlite3.connect(ledger_db, timeout=30, isolation_level=None) as db:
            db.execute("PRAGMA busy_timeout=30000")
            db.execute("PRAGMA foreign_keys=ON")
            db.executescript(_SCHEMA)
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM used_nonces WHERE expires_at < ?", (current_epoch,))
            try:
                db.execute("INSERT INTO used_nonces VALUES (?, ?, ?)",
                    (envelope["agent_id"], envelope["nonce"], nonce_expiry))
            except sqlite3.IntegrityError as exc:
                raise AtomicSyncReceiptError("Rejeu détecté : nonce déjà consommé.") from exc

            payload = envelope["payload"]
            existing = db.execute(
                "SELECT approval_id, owner_id, source_instance_id, destination_instance_id, "
                "export_id, event_count FROM sync_bundle_receipts WHERE bundle_digest=?",
                (bundle["bundle_digest"],)).fetchone()
            if existing:
                expected = (owner_id, bundle["source_instance_id"], bundle["destination_instance_id"],
                    bundle["export_id"], len(bundle["events"]))
                if existing[1:] != expected:
                    raise AtomicSyncReceiptError("Digest déjà enregistré avec des métadonnées divergentes.")
                receipt_approval_id = existing[0]
                status = "already_recorded"
            else:
                db.execute("INSERT INTO sync_bundle_receipts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (bundle["bundle_digest"], payload["approval_id"], owner_id,
                     bundle["source_instance_id"], bundle["destination_instance_id"],
                     bundle["export_id"], len(bundle["events"]), recorded_at,
                     "verified_pending_manual_import"))
                for event in bundle["events"]:
                    db.execute("INSERT INTO sync_bundle_receipt_items "
                        "(event_id,kind,record_id,content_digest,sequence,bundle_digest) VALUES (?,?,?,?,?,?)",
                        (event["event_id"], event["kind"], event["record_id"],
                         event["content_digest"], event["sequence"], bundle["bundle_digest"]))
                receipt_approval_id = payload["approval_id"]
                status = "recorded"
            db.execute("COMMIT")
    except AtomicSyncReceiptError:
        raise
    except sqlite3.IntegrityError as exc:
        raise AtomicSyncReceiptError(
            "Collision d'événement, de ressource ou d'approbation; transaction annulée.") from exc
    except sqlite3.Error as exc:
        raise AtomicSyncReceiptError("Échec SQLite; transaction annulée.") from exc

    os.chmod(ledger_db, 0o600)
    return {"status": status, "bundle_digest": bundle["bundle_digest"],
        "approval_id": receipt_approval_id, "latest_verified_approval_id": verified["approval_id"],
        "event_count": verified["event_count"], "nonce_consumed_atomically": True,
        "receipt_committed": True, "import_performed": False,
        "execution_enabled": False, "ledger_scope": "single_instance_local"}
