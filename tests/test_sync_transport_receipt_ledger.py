import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from papi_core.identity_ed25519 import provision_ed25519_agent, sign_ed25519_request
from papi_core.sync_transport_receipt_ledger import (
    SyncTransportReceiptLedgerError, record_verified_sync_transport_receipt,
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
        self.replay, self.ledger = self.root / "replay.sqlite3", self.root / "ledger.sqlite3"

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
        self.assertFalse(self.ledger.exists())

    def test_corrupt_request_not_recorded(self):
        self.request["body"]["package_base64"] = "tampered"
        with self.assertRaises(SyncTransportReceiptLedgerError):
            self.record(self.receipt())
        self.assertFalse(self.ledger.exists())


if __name__ == "__main__":
    unittest.main()
