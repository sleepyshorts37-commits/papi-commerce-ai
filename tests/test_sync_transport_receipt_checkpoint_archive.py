import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from papi_core.identity_ed25519 import provision_ed25519_agent
from papi_core.sync_transport_receipt_checkpoint import (
    create_sync_transport_receipt_checkpoint,
)
from papi_core.sync_transport_receipt_checkpoint_archive import (
    SyncTransportReceiptCheckpointArchiveError,
    archive_sync_transport_receipt_checkpoint,
    audit_sync_transport_receipt_checkpoint_archive,
)


class SyncTransportReceiptCheckpointArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = self.root / "registry.json"
        self.private_key = provision_ed25519_agent(
            "archive-owner", self.root / "keys", self.registry
        )
        self.ledger = self.root / "ledger.sqlite3"
        self.archive = self.root / "checkpoints.sqlite3"
        with sqlite3.connect(self.ledger) as db:
            db.executescript("""
                CREATE TABLE sync_transport_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    delivery_id TEXT NOT NULL UNIQUE,
                    request_body_sha256 TEXT NOT NULL,
                    source_instance_id TEXT NOT NULL,
                    destination_instance_id TEXT NOT NULL,
                    receipt_sha256 TEXT NOT NULL UNIQUE,
                    receipt_json TEXT NOT NULL,
                    verified_at TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status='verified_transport_receipt')
                );
                CREATE TRIGGER sync_transport_receipts_no_update
                BEFORE UPDATE ON sync_transport_receipts
                BEGIN SELECT RAISE(ABORT, 'append-only'); END;
                CREATE TRIGGER sync_transport_receipts_no_delete
                BEFORE DELETE ON sync_transport_receipts
                BEGIN SELECT RAISE(ABORT, 'append-only'); END;
            """)
        self.checkpoint = create_sync_transport_receipt_checkpoint(
            ledger_db=self.ledger, agent_id="archive-owner",
            private_key_path=self.private_key, timestamp=1794657600,
        )

    def tearDown(self):
        self.temp.cleanup()

    def archive_checkpoint(self):
        return archive_sync_transport_receipt_checkpoint(
            checkpoint=self.checkpoint, archive_db=self.archive,
            ledger_db=self.ledger, registry_path=self.registry, now=1794657600,
        )

    def audit(self):
        return audit_sync_transport_receipt_checkpoint_archive(
            archive_db=self.archive, registry_path=self.registry, now=1794657600,
        )

    def test_archive_and_read_only_signature_audit(self):
        result = self.archive_checkpoint()
        self.assertEqual(result["status"], "archived")
        self.assertTrue(self.audit()["signatures_verified"])
        self.assertEqual(self.audit()["records_audited"], 1)

    def test_archived_signature_remains_auditable_after_clock_window(self):
        self.archive_checkpoint()
        result = audit_sync_transport_receipt_checkpoint_archive(
            archive_db=self.archive, registry_path=self.registry,
            now=1794657600 + 86400,
        )
        self.assertEqual(result["records_audited"], 1)
        self.assertTrue(result["signatures_verified"])

    def test_archive_remains_auditable_after_signing_key_rotation(self):
        self.archive_checkpoint()
        from papi_core.identity_ed25519 import rotate_ed25519_agent
        rotate_ed25519_agent("archive-owner", self.root / "keys", self.registry)
        result = self.audit()
        self.assertEqual(result["records_audited"], 1)
        self.assertTrue(result["signatures_verified"])

    def test_archive_remains_auditable_after_signing_key_revocation(self):
        self.archive_checkpoint()
        from papi_core.identity_ed25519 import revoke_ed25519_agent
        revoke_ed25519_agent("archive-owner", self.registry)
        result = self.audit()
        self.assertEqual(result["records_audited"], 1)
        self.assertTrue(result["signatures_verified"])

    def test_exact_duplicate_is_idempotent(self):
        self.assertEqual(self.archive_checkpoint()["status"], "archived")
        duplicate = self.archive_checkpoint()
        self.assertEqual(duplicate["status"], "already_archived")
        self.assertFalse(duplicate["archive_modified"])

    def test_archive_is_append_only(self):
        self.archive_checkpoint()
        with sqlite3.connect(self.archive) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "UPDATE sync_transport_receipt_checkpoints SET checkpoint_json='{}'"
                )
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM sync_transport_receipt_checkpoints")

    def test_tampering_is_detected_after_trigger_bypass(self):
        self.archive_checkpoint()
        with sqlite3.connect(self.archive) as db:
            db.execute("DROP TRIGGER sync_transport_receipt_checkpoints_no_update")
            db.execute(
                "UPDATE sync_transport_receipt_checkpoints SET checkpoint_json=?",
                (json.dumps({"schema_version": 1}),),
            )
        with self.assertRaises(SyncTransportReceiptCheckpointArchiveError):
            self.audit()

    def test_archived_signature_can_be_audited_after_ledger_changes(self):
        self.archive_checkpoint()
        # The historical archive audit verifies the signed snapshot itself,
        # independently of whether that snapshot still matches today's ledger.
        with sqlite3.connect(self.ledger) as db:
            db.execute("DROP TRIGGER sync_transport_receipts_no_update")
            db.execute("INSERT INTO sync_transport_receipts VALUES (?,?,?,?,?,?,?,?,?)",
                       ("r1", "d1", "a" * 64, "src", "dst", "b" * 64,
                        json.dumps({"payload": {"receipt_id": "r1", "delivery_id": "d1"}}),
                        "2026-11-14T00:00:00Z", "verified_transport_receipt"))
        self.assertEqual(self.audit()["records_audited"], 1)


if __name__ == "__main__":
    unittest.main()
