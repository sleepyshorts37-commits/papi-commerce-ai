import hashlib
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from papi_core.identity_ed25519 import provision_ed25519_agent
from papi_core.sync_bundle import build_sync_bundle
from papi_core.sync_bundle_approval import sign_sync_bundle_approval
from papi_core.sync_receiver import SyncReceiverError, receive_sync_package
from papi_core.sync_spool import write_sync_package

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)


class SyncReceiverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = self.root / "public.json"
        self.private = provision_ed25519_agent("owner-44", self.root / "keys", self.registry)
        self.ledger = self.root / "receiver.sqlite3"
        self.spool = self.root / "spool"
        self.bundle = build_sync_bundle(
            source_instance_id="instance-source",
            destination_instance_id="instance-target",
            export_id="export-44",
            created_at="2026-11-14T11:59:00Z",
            cursor_start=1,
            cursor_end=1,
            events=[{
                "event_id": "evt-44-a", "kind": "memory", "record_id": "MEM-44-A",
                "sequence": 1, "content_digest": hashlib.sha256(b"synthetic-44").hexdigest(),
            }],
        )
        self.approval = sign_sync_bundle_approval(
            owner_id="owner-44", private_key_path=self.private, bundle=self.bundle,
            approval_id="APR-44", issued_at="2026-11-14T12:00:00Z",
            expires_at="2026-11-14T12:10:00Z",
            nonce="nonce-receiver-44-0001", timestamp=int(NOW.timestamp()),
        )
        written = write_sync_package(bundle=self.bundle, approval=self.approval, spool_dir=self.spool)
        self.package_path = Path(written["path"])

    def tearDown(self):
        self.temp.cleanup()

    def receive(self, **overrides):
        args = {
            "package_path": self.package_path, "owner_id": "owner-44",
            "registry_path": self.registry, "ledger_db": self.ledger,
            "expected_destination": "instance-target",
            "now_epoch": int(NOW.timestamp()), "now": NOW,
        }
        args.update(overrides)
        return receive_sync_package(**args)

    def counts(self):
        with sqlite3.connect(self.ledger) as db:
            return (
                db.execute("SELECT COUNT(*) FROM used_nonces").fetchone()[0],
                db.execute("SELECT COUNT(*) FROM sync_bundle_receipts").fetchone()[0],
                db.execute("SELECT COUNT(*) FROM sync_bundle_receipt_items").fetchone()[0],
            )

    def test_receiver_authenticates_and_records_without_import(self):
        result = self.receive()
        self.assertTrue(result["signature_verified"])
        self.assertTrue(result["nonce_consumed_atomically"])
        self.assertTrue(result["receipt_committed"])
        self.assertTrue(result["package_retained"])
        self.assertFalse(result["import_performed"])
        self.assertFalse(result["execution_enabled"])
        self.assertEqual(result["event_count"], 1)
        self.assertTrue(self.package_path.exists())
        self.assertEqual(self.counts(), (1, 1, 1))

    def test_replay_is_rejected_without_duplicate_receipt(self):
        self.receive()
        with self.assertRaises(SyncReceiverError):
            self.receive()
        self.assertEqual(self.counts(), (1, 1, 1))

    def test_wrong_destination_fails_before_ledger_creation(self):
        with self.assertRaises(SyncReceiverError):
            self.receive(expected_destination="instance-other")
        self.assertFalse(self.ledger.exists())

    def test_unknown_owner_fails_closed(self):
        with self.assertRaises(SyncReceiverError):
            self.receive(owner_id="someone-else")
        self.assertFalse(self.ledger.exists())

    def test_tampered_package_fails_before_receipt(self):
        raw = self.package_path.read_bytes()
        self.package_path.write_bytes(raw + b" ")
        with self.assertRaises(SyncReceiverError):
            self.receive()
        self.assertFalse(self.ledger.exists())

    def test_expired_approval_fails_before_receipt(self):
        expired = datetime(2026, 11, 14, 12, 11, tzinfo=timezone.utc)
        with self.assertRaises(SyncReceiverError):
            self.receive(now=expired, now_epoch=int(expired.timestamp()))
        self.assertFalse(self.ledger.exists())

    def test_second_approval_for_same_bundle_is_idempotent(self):
        first = self.receive()
        second_approval = sign_sync_bundle_approval(
            owner_id="owner-44", private_key_path=self.private, bundle=self.bundle,
            approval_id="APR-44-RETRY", issued_at="2026-11-14T12:00:00Z",
            expires_at="2026-11-14T12:10:00Z",
            nonce="nonce-receiver-44-0002", timestamp=int(NOW.timestamp()),
        )
        second_package = write_sync_package(
            bundle=self.bundle, approval=second_approval, spool_dir=self.root / "retry-spool"
        )
        result = self.receive(package_path=Path(second_package["path"]))
        self.assertEqual(first["status"], "recorded")
        self.assertEqual(result["status"], "already_recorded")
        self.assertEqual(self.counts(), (2, 1, 1))


if __name__ == "__main__":
    unittest.main()
