import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from papi_core.identity_ed25519 import provision_ed25519_agent, sign_ed25519_request
from papi_core.sync_transport_receipt_ledger import (
    SyncTransportReceiptLedgerError, audit_sync_transport_receipt_ledger,\n    record_verified_sync_transport_receipt,
)


class SyncTransportReceiptLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = self.root / "registry.json"
        provision_ed25519_agent("source-58", self.root / "keys", self.registry)
        self.key = provision_ed25519_agent("target-58", self.root / "keys", self.registry)
        self.manifest = {
            "delivery_id": "d" * 64, "source_instance_id": "source-58",
            "destination_instance_id": "target-58",
            "package": {"package_digest": "a" * 64},
            "payload": {"payload_digest": "b" * 64},
        }
        self.body = {
            "protocol": "papi.sync.transport-request", "protocol_version": 1,
            "delivery_id": self.manifest["delivery_id"],
            "source_instance_id": "source-58", "destination_instance_id": "target-58",
            "manifest": self.manifest, "package_base64": "cGFja2FnZQ==",
            "payload_base64": "cGF5bG9hZA==",
        }
        raw = json.dumps(self.body, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode()
        self.request = {
            "method": "POST", "url": "https://sync.example.com/v1/receive",
            "headers": {"Content-Type": "application/json", "Accept": "application/json",
                        "Idempotency-Key": self.manifest["delivery_id"]},
            "body": self.body, "body_sha256": hashlib.sha256(raw).hexdigest(),
            "body_size_bytes": len(raw), "network_transfer_performed": False,
            "nonce_consumed": False, "receipt_committed": False,
            "import_performed": False, "execution_enabled": False,
            "receiver_authentication_required": True,
            "receiver_reverification_required": True, "tls_verification_required": True,
            "redirects_allowed": False,
        }
        self.replay = self.ledger = self.root / "ledger.sqlite3"

    def tearDown(self):
        self.temp.cleanup()

    def receipt(self, receipt_id="receipt-58-001", nonce="nonce-receipt-58-0001", **changes):
        payload = {
            "scope": "papi.sync.transport-receipt", "decision": "accepted",
            "receipt_id": receipt_id, "delivery_id": self.manifest["delivery_id"],
            "request_body_sha256": self.request["body_sha256"],
            "source_instance_id": "source-58", "destination_instance_id": "target-58",
            "package_digest": "a" * 64, "payload_digest": "b" * 64,
        }
        payload.update(changes)
        return sign_ed25519_request(
            "target-58", payload, self.key, timestamp=1794657600, nonce=nonce,
        )

    def record(self, receipt):
        return record_verified_sync_transport_receipt(
            request=self.request, receipt=receipt, registry_path=self.registry,
            replay_db=self.replay, ledger_db=self.ledger, now=1794657600,
        )

    def test_records_verified_receipt(self):
        result = self.record(self.receipt())
        self.assertEqual(result["status"], "recorded")
        self.assertTrue(result["receipt_committed"])
        self.assertTrue(result["destination_nonce_consumed"])
        self.assertFalse(result["network_transfer_performed"])
        with sqlite3.connect(self.ledger) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM sync_transport_receipts").fetchone()[0], 1)

    def test_exact_repeat_is_idempotent_without_replay_failure(self):
        receipt = self.receipt()
        self.assertEqual(self.record(receipt)["status"], "recorded")
        self.assertEqual(self.record(receipt)["status"], "already_recorded")

    def test_conflicting_receipt_for_same_delivery_rejected(self):
        self.record(self.receipt())
        with self.assertRaises(SyncTransportReceiptLedgerError):
            self.record(self.receipt(receipt_id="receipt-58-other", nonce="nonce-receipt-58-0002"))

    def test_invalid_signature_not_recorded(self):
        receipt = self.receipt()
        receipt["payload"]["decision"] = "rejected"
        with self.assertRaises(SyncTransportReceiptLedgerError):
            self.record(receipt)
        with sqlite3.connect(self.ledger) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM sync_transport_receipts").fetchone()[0], 0)
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "used_nonces" in tables:
                self.assertEqual(db.execute("SELECT count(*) FROM used_nonces").fetchone()[0], 0)

    def test_corrupt_request_not_recorded(self):
        self.request["body"]["package_base64"] = "tampered"
        with self.assertRaises(SyncTransportReceiptLedgerError):
            self.record(self.receipt())
        if self.ledger.exists():
            with sqlite3.connect(self.ledger) as db:
                tables = {row[0] for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )}
                if "sync_transport_receipts" in tables:
                    self.assertEqual(db.execute(
                        "SELECT count(*) FROM sync_transport_receipts"
                    ).fetchone()[0], 0)
                if "used_nonces" in tables:
                    self.assertEqual(db.execute(
                        "SELECT count(*) FROM used_nonces"
                    ).fetchone()[0], 0)

    def test_nonce_and_receipt_share_one_database(self):
        result = self.record(self.receipt())
        self.assertTrue(result["nonce_and_receipt_atomic"])
        with sqlite3.connect(self.ledger) as db:
            receipt_count = db.execute(
                "SELECT count(*) FROM sync_transport_receipts"
            ).fetchone()[0]
            nonce_count = db.execute(
                "SELECT count(*) FROM used_nonces WHERE agent_id='target-58'"
            ).fetchone()[0]
        self.assertEqual(receipt_count, 1)
        self.assertEqual(nonce_count, 1)

    def test_receipt_insert_failure_rolls_back_nonce(self):
        with sqlite3.connect(self.ledger) as db:
            db.execute("""
                CREATE TABLE sync_transport_receipts (
                    receipt_id TEXT PRIMARY KEY, delivery_id TEXT NOT NULL UNIQUE,
                    request_body_sha256 TEXT NOT NULL, source_instance_id TEXT NOT NULL,
                    destination_instance_id TEXT NOT NULL, receipt_sha256 TEXT NOT NULL UNIQUE,
                    receipt_json TEXT NOT NULL,
                    verified_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    status TEXT NOT NULL CHECK(status = 'verified_transport_receipt')
                )
            """)
            db.execute("""
                CREATE TRIGGER reject_receipt BEFORE INSERT ON sync_transport_receipts
                BEGIN SELECT RAISE(ABORT, 'injected ledger write failure'); END
            """)
        with self.assertRaises(SyncTransportReceiptLedgerError):
            self.record(self.receipt())
        with sqlite3.connect(self.ledger) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM sync_transport_receipts").fetchone()[0], 0)
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "used_nonces" in tables:
                self.assertEqual(db.execute("SELECT count(*) FROM used_nonces").fetchone()[0], 0)

    def test_ledger_blocks_update_and_delete(self):
        self.record(self.receipt())
        with sqlite3.connect(self.ledger) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE sync_transport_receipts SET status='changed'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM sync_transport_receipts")
        self.assertEqual(audit_sync_transport_receipt_ledger(
            ledger_db=self.ledger
        )["records_audited"], 1)

    def test_read_only_audit_detects_receipt_tampering(self):
        self.record(self.receipt())
        with sqlite3.connect(self.ledger) as db:
            db.execute("DROP TRIGGER sync_transport_receipts_no_update")
            db.execute("UPDATE sync_transport_receipts SET receipt_json='{}'")
        with self.assertRaises(SyncTransportReceiptLedgerError):
            audit_sync_transport_receipt_ledger(ledger_db=self.ledger)

    def test_separate_replay_database_is_rejected(self):
        with self.assertRaises(SyncTransportReceiptLedgerError):
            record_verified_sync_transport_receipt(
                request=self.request, receipt=self.receipt(),
                registry_path=self.registry, replay_db=self.root / "other.sqlite3",
                ledger_db=self.ledger, now=1794657600,
            )
        self.assertFalse((self.root / "other.sqlite3").exists())
        self.assertFalse(self.ledger.exists())


if __name__ == "__main__":
    unittest.main()
