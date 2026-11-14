"""Import contrôlé atomique des contenus approuvés dans le magasin SQLite local."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .identity_ed25519 import MAX_CLOCK_SKEW_SECONDS
from .sync_bundle_approval import SyncBundleApprovalError, verify_sync_bundle_approval
from .sync_payload import SyncPayloadError, read_sync_payload


class SyncImportError(ValueError):
    """Import refusé ou annulé intégralement."""


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
CREATE TABLE IF NOT EXISTS sync_import_batches (
 bundle_digest TEXT PRIMARY KEY REFERENCES sync_bundle_receipts(bundle_digest),
 payload_digest TEXT NOT NULL, imported_at TEXT NOT NULL,
 record_count INTEGER NOT NULL CHECK(record_count BETWEEN 0 AND 500)
);
CREATE TABLE IF NOT EXISTS sync_imported_records (
 event_id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('memory','message')),
 record_id TEXT NOT NULL, content_digest TEXT NOT NULL,
 record_json TEXT NOT NULL, bundle_digest TEXT NOT NULL
 REFERENCES sync_import_batches(bundle_digest),
 UNIQUE(kind, record_id)
);
"""


def import_approved_sync_content(
    *, package_path: Path, payload_path: Path, owner_id: str,
    registry_path: Path, ledger_db: Path, expected_destination: str,
    agents_path: Path, now_epoch: int | None = None,
    now: datetime | None = None, max_approval_ttl_seconds: int = 900,
) -> dict[str, Any]:
    """Vérifie paquet, signature, payload puis consomme nonce et importe en une transaction."""
    from .sync_spool import SyncSpoolError, read_sync_package

    try:
        package = read_sync_package(Path(package_path))
        bundle = package["bundle"]
        payload = read_sync_payload(Path(payload_path), bundle=bundle, agents_path=Path(agents_path))
        verified = verify_sync_bundle_approval(
            envelope=package["approval"], bundle=bundle, owner_id=owner_id,
            registry_path=Path(registry_path), replay_db=Path(ledger_db),
            expected_destination=expected_destination, now_epoch=now_epoch,
            now=now, max_approval_ttl_seconds=max_approval_ttl_seconds,
            consume_nonce=False,
        )
    except (SyncSpoolError, SyncPayloadError, SyncBundleApprovalError, KeyError, TypeError) as exc:
        raise SyncImportError(f"Paquet, approbation ou contenu refusé : {exc}") from exc

    envelope = package["approval"]
    epoch = int(now_epoch if now_epoch is not None else datetime.now(timezone.utc).timestamp())
    nonce_expiry = envelope["timestamp"] + MAX_CLOCK_SKEW_SECONDS
    imported_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    db_path = Path(ledger_db)
    db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    records = payload["records"]
    try:
        with sqlite3.connect(db_path, timeout=30, isolation_level=None) as db:
            db.execute("PRAGMA busy_timeout=30000")
            db.execute("PRAGMA foreign_keys=ON")
            db.executescript(_SCHEMA)
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM used_nonces WHERE expires_at < ?", (epoch,))
            db.execute("INSERT INTO used_nonces VALUES (?, ?, ?)",
                       (envelope["agent_id"], envelope["nonce"], nonce_expiry))
            digest = bundle["bundle_digest"]
            existing = db.execute(
                "SELECT payload_digest, record_count FROM sync_import_batches WHERE bundle_digest=?",
                (digest,),
            ).fetchone()
            if existing:
                if existing != (payload["payload_digest"], len(records)):
                    raise SyncImportError("Bundle déjà importé avec un contenu divergent.")
                status = "already_imported"
            else:
                receipt = db.execute(
                    "SELECT owner_id,source_instance_id,destination_instance_id,export_id,event_count "
                    "FROM sync_bundle_receipts WHERE bundle_digest=?", (digest,),
                ).fetchone()
                expected = (owner_id, bundle["source_instance_id"], bundle["destination_instance_id"],
                            bundle["export_id"], len(bundle["events"]))
                if receipt and receipt != expected:
                    raise SyncImportError("Reçu existant avec des métadonnées divergentes.")
                if not receipt:
                    db.execute("INSERT INTO sync_bundle_receipts VALUES (?,?,?,?,?,?,?,?,?)",
                        (digest, envelope["payload"]["approval_id"], owner_id,
                         bundle["source_instance_id"], bundle["destination_instance_id"],
                         bundle["export_id"], len(bundle["events"]), imported_at,
                         "verified_pending_manual_import"))
                    for event in bundle["events"]:
                        db.execute(
                            "INSERT INTO sync_bundle_receipt_items "
                            "(event_id,kind,record_id,content_digest,sequence,bundle_digest) "
                            "VALUES (?,?,?,?,?,?)",
                            (event["event_id"], event["kind"], event["record_id"],
                             event["content_digest"], event["sequence"], digest),
                        )
                db.execute("INSERT INTO sync_import_batches VALUES (?,?,?,?)",
                           (digest, payload["payload_digest"], imported_at, len(records)))
                for item in records:
                    db.execute(
                        "INSERT INTO sync_imported_records "
                        "(event_id,kind,record_id,content_digest,record_json,bundle_digest) "
                        "VALUES (?,?,?,?,?,?)",
                        (item["event_id"], item["kind"], item["record_id"],
                         item["content_digest"],
                         json.dumps(item["record"], ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False), digest),
                    )
                status = "imported"
            db.execute("COMMIT")
    except SyncImportError:
        raise
    except sqlite3.IntegrityError as exc:
        raise SyncImportError("Rejeu ou collision de contenu; nonce, reçu et import annulés.") from exc
    except sqlite3.Error as exc:
        raise SyncImportError("Erreur SQLite; transaction d'import annulée.") from exc

    os.chmod(db_path, 0o600)
    return {
        "status": status, "bundle_digest": bundle["bundle_digest"],
        "payload_digest": payload["payload_digest"], "approval_id": verified["approval_id"], "signature_verified": True,
        "destination_instance_id": expected_destination, "imported_records": len(records),
        "nonce_consumed_atomically": True, "receipt_and_content_committed_atomically": True,
        "storage": "local_sqlite_import_store", "source_files_retained": True,
        "memory_chat_jsonl_modified": False, "execution_enabled": False,
    }
