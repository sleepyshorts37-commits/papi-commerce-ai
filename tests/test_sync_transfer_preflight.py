import hashlib
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from papi_core.identity_ed25519 import provision_ed25519_agent
from papi_core.sync_bundle import build_sync_bundle
from papi_core.sync_bundle_approval import sign_sync_bundle_approval
from papi_core.sync_payload import write_sync_payload
from papi_core.sync_spool import write_sync_package
from papi_core.sync_transfer_manifest import build_sync_transfer_manifest
from papi_core.sync_transfer_preflight import (
    SyncTransferPreflightError, preflight_sync_transfer,
)

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)


class SyncTransferPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = self.root / "public.json"
        self.private = provision_ed25519_agent("owner-55", self.root / "keys", self.registry)
        self.replay = self.root / "replay.sqlite3"
        self.bundle = build_sync_bundle(
            source_instance_id="instance-source", destination_instance_id="instance-target",
            export_id="export-55", created_at="2026-11-14T11:59:00Z",
            cursor_start=1, cursor_end=0, events=[],
        )
        self.approval = sign_sync_bundle_approval(
            owner_id="owner-55", private_key_path=self.private, bundle=self.bundle,
            approval_id="APR-55", issued_at="2026-11-14T12:00:00Z",
            expires_at="2026-11-14T12:10:00Z",
            nonce="nonce-preflight-55-0001", timestamp=int(NOW.timestamp()),
        )
        package = write_sync_package(
            bundle=self.bundle, approval=self.approval, spool_dir=self.root)
        payload = write_sync_payload(bundle=self.bundle, records=[], spool_dir=self.root)
        self.package_path = Path(package["path"])
        self.payload_path = Path(payload["path"])
        self.manifest = build_sync_transfer_manifest(
            package_path=self.package_path, payload_path=self.payload_path)

    def tearDown(self):
        self.temp.cleanup()

    def run_preflight(self, **overrides):
        args = dict(
            manifest=self.manifest, directory=self.root, owner_id="owner-55",
            registry_path=self.registry, replay_db=self.replay,
            expected_destination="instance-target", now_epoch=int(NOW.timestamp()), now=NOW,
        )
        args.update(overrides)
        return preflight_sync_transfer(**args)

    def test_valid_transfer_is_verified_without_consuming_nonce(self):
        result = self.run_preflight()
        self.assertEqual(result["status"], "preflight_verified")
        self.assertTrue(result["signature_verified"])
        self.assertFalse(result["nonce_consumed"])
        self.assertFalse(result["receipt_committed"])
        self.assertFalse(result["import_performed"])
        self.assertFalse(result["network_transfer_performed"])
        self.assertFalse(result["execution_enabled"])
        self.assertTrue(result["receiver_reverification_required"])
        self.assertFalse(self.replay.exists())

    def test_wrong_destination_is_rejected_without_writes(self):
        with self.assertRaises(SyncTransferPreflightError):
            self.run_preflight(expected_destination="instance-other")
        self.assertFalse(self.replay.exists())

    def test_unknown_owner_is_rejected(self):
        with self.assertRaises(SyncTransferPreflightError):
            self.run_preflight(owner_id="not-owner")
        self.assertFalse(self.replay.exists())

    def test_tampered_payload_is_rejected(self):
        self.payload_path.write_bytes(self.payload_path.read_bytes() + b"x")
        with self.assertRaises(SyncTransferPreflightError):
            self.run_preflight()
        self.assertFalse(self.replay.exists())

    def test_expired_approval_is_rejected(self):
        later = datetime(2026, 11, 14, 12, 11, tzinfo=timezone.utc)
        with self.assertRaises(SyncTransferPreflightError):
            self.run_preflight(now=later, now_epoch=int(later.timestamp()))
        self.assertFalse(self.replay.exists())


if __name__ == "__main__":
    unittest.main()
