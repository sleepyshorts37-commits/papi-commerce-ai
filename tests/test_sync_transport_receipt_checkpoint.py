import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from papi_core.identity_ed25519 import provision_ed25519_agent
from papi_core.sync_transport_receipt_checkpoint import (
    SyncTransportReceiptCheckpointError,
    create_sync_transport_receipt_checkpoint,
    verify_sync_transport_receipt_checkpoint,
)
from papi_core.sync_transport_receipt_ledger import record_verified_sync_transport_receipt


class SyncTransportReceiptCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = self.root / "registry.json"
        self.private_key = provision_ed25519_agent(
            "checkpoint-owner", self.root / "keys", self.registry
        )
        self.db = self.root / "ledger.sqlite3"
        # A valid empty append-only ledger is sufficient to exercise snapshot signing.
        with sqlite3.connect(self.db) as connection:
            connection.executescript("""
                CREATE TABLE sync_transport_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    delivery_id TEXT NOT NULL UNIQUE,
                    request_body_sha256 TEXT NOT NULL,
                    source_instance_id TEXT NOT NULL,
                    destination_instance_id TEXT NOT NULL,
                    receipt_sha256 TEXT NOT NULL UNIQUE,
                    receipt_json TEXT NOT NULL,
                    verified_at TEXT NOT NULL,
                    status TEXT NOT NULL
                );
                CREATE TRIGGER sync_transport_receipts_no_update
                BEFORE UPDATE ON sync_transport_receipts
                BEGIN SELECT RAISE(ABORT, 'append-only'); END;
                CREATE TRIGGER sync_transport_receipts_no_delete
                BEFORE DELETE ON sync_transport_receipts
                BEGIN SELECT RAISE(ABORT, 'append-only'); END;
            """)

    def tearDown(self):
        self.temp.cleanup()

    def create(self):
        return create_sync_transport_receipt_checkpoint(
            ledger_db=self.db, agent_id="checkpoint-owner",
            private_key_path=self.private_key, timestamp=1794657600,
        )

    def verify(self, checkpoint):
        return verify_sync_transport_receipt_checkpoint(
            checkpoint=checkpoint, ledger_db=self.db,
            registry_path=self.registry, now=1794657600,
        )

    def test_signed_checkpoint_verifies_without_mutating_ledger(self):
        before = self.db.read_bytes()
        checkpoint = self.create()
        result = self.verify(checkpoint)
        self.assertEqual(result["status"], "checkpoint_verified")
        self.assertTrue(result["signature_verified"])
        self.assertFalse(result["nonce_consumed"])
        self.assertEqual(self.db.read_bytes(), before)

    def test_checkpoint_detects_inserted_receipt_after_signing(self):
        checkpoint = self.create()
        with sqlite3.connect(self.db) as connection:
            connection.execute(
                "INSERT INTO sync_transport_receipts VALUES (?,?,?,?,?,?,?,?,?)",
                ("r1", "d1", "a" * 64, "source", "target", "b" * 64,
                 json.dumps({"payload": {"receipt_id": "r1", "delivery_id": "d1"}}),
                 "2026-11-14T00:00:00Z", "verified_transport_receipt"),
            )
        with self.assertRaises(SyncTransportReceiptCheckpointError):
            self.verify(checkpoint)

    def test_modified_signature_is_rejected(self):
        checkpoint = self.create()
        checkpoint["envelope"]["signature"] = "00" * 64
        with self.assertRaises(SyncTransportReceiptCheckpointError):
            self.verify(checkpoint)

    def test_modified_signed_payload_is_rejected(self):
        checkpoint = self.create()
        checkpoint["envelope"]["payload"]["records_count"] = 99
        with self.assertRaises(SyncTransportReceiptCheckpointError):
            self.verify(checkpoint)

    def test_checkpoint_metadata_cannot_claim_external_actions(self):
        checkpoint = self.create()
        checkpoint["network_transfer_performed"] = True
        with self.assertRaises(SyncTransportReceiptCheckpointError):
            self.verify(checkpoint)


if __name__ == "__main__":
    unittest.main()
