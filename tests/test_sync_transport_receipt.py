import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from papi_core.identity_ed25519 import provision_ed25519_agent, sign_ed25519_request
from papi_core.sync_transport_receipt import (
    SyncTransportReceiptError, verify_sync_transport_receipt,
)

class SyncTransportReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = self.root / "public.json"
        self.source_key = provision_ed25519_agent("source-57", self.root / "keys", self.registry)
        self.destination_key = provision_ed25519_agent("target-57", self.root / "keys", self.registry)
        self.manifest = {
            "delivery_id": "d" * 64, "source_instance_id": "source-57",
            "destination_instance_id": "target-57",
            "package": {"package_digest": "a" * 64},
            "payload": {"payload_digest": "b" * 64},
        }
        self.body = {
            "protocol": "papi.sync.transport-request", "protocol_version": 1,
            "delivery_id": self.manifest["delivery_id"],
            "source_instance_id": "source-57", "destination_instance_id": "target-57",
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
        self.replay = self.root / "replay.sqlite3"

    def tearDown(self):
        self.temp.cleanup()

    def receipt(self, **changes):
        payload = {
            "scope": "papi.sync.transport-receipt", "decision": "accepted",
            "receipt_id": "receipt-57-001",
            "delivery_id": self.manifest["delivery_id"],
            "request_body_sha256": self.request["body_sha256"],
            "source_instance_id": "source-57", "destination_instance_id": "target-57",
            "package_digest": "a" * 64, "payload_digest": "b" * 64,
        }
        payload.update(changes)
        return sign_ed25519_request(
            "target-57", payload, self.destination_key, timestamp=1794657600,
            nonce="nonce-receipt-57-0001",
        )

    def verify(self, receipt):
        return verify_sync_transport_receipt(
            request=self.request, receipt=receipt, registry_path=self.registry,
            replay_db=self.replay, now=1794657600,
        )

    def test_accepts_exact_signed_destination_receipt(self):
        result = self.verify(self.receipt())
        self.assertEqual(result["status"], "transport_receipt_verified")
        self.assertTrue(result["destination_signature_verified"])
        self.assertTrue(result["destination_nonce_consumed"])
        self.assertFalse(result["network_transfer_performed"])
        self.assertFalse(result["receipt_committed"])
        self.assertFalse(result["import_performed"])

    def test_rejects_receipt_from_wrong_signer(self):
        receipt = sign_ed25519_request(
            "source-57", self.receipt().get("payload"), self.source_key,
            timestamp=1794657600, nonce="nonce-wrong-signer-57",
        )
        with self.assertRaises(SyncTransportReceiptError):
            self.verify(receipt)

    def test_rejects_mismatched_delivery_and_does_not_consume_nonce(self):
        receipt = self.receipt(delivery_id="e" * 64)
        with self.assertRaises(SyncTransportReceiptError):
            self.verify(receipt)
        self.assertFalse(self.replay.exists())

    def test_rejects_tampered_request_body_digest(self):
        self.request["body"]["package_base64"] = "dGFtcGVy"
        with self.assertRaises(SyncTransportReceiptError):
            self.verify(self.receipt())

    def test_rejects_wrong_payload_digest(self):
        with self.assertRaises(SyncTransportReceiptError):
            self.verify(self.receipt(payload_digest="f" * 64))

    def test_rejects_replayed_receipt_nonce(self):
        receipt = self.receipt()
        self.verify(receipt)
        with self.assertRaises(SyncTransportReceiptError):
            self.verify(receipt)

    def test_rejects_non_accepted_decision(self):
        with self.assertRaises(SyncTransportReceiptError):
            self.verify(self.receipt(decision="rejected"))

if __name__ == "__main__":
    unittest.main()
