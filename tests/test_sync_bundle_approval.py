import hashlib
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from papi_core.identity_ed25519 import provision_ed25519_agent, sign_ed25519_request
from papi_core.sync_bundle import build_sync_bundle
from papi_core.sync_bundle_approval import (
    SyncBundleApprovalError, sign_sync_bundle_approval, verify_sync_bundle_approval,
)

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)


def make_bundle():
    return build_sync_bundle(
        source_instance_id="instance-a", destination_instance_id="instance-b",
        export_id="export-40", created_at="2026-11-14T11:59:00Z",
        cursor_start=1, cursor_end=1,
        events=[{"event_id": "evt-40", "kind": "memory", "record_id": "MEM-40",
                 "sequence": 1, "content_digest": hashlib.sha256(b"synthetic").hexdigest()}],
    )


class SyncBundleApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.registry, self.replay = root / "public.json", root / "replay.sqlite3"
        self.private = provision_ed25519_agent("owner-40", root / "keys", self.registry)
        self.bundle = make_bundle()

    def tearDown(self):
        self.temp.cleanup()

    def sign(self, **changes):
        # Re-sign altered payloads to test semantic scope checks, not only signature failure.
        envelope = sign_sync_bundle_approval(
            owner_id="owner-40", private_key_path=self.private, bundle=self.bundle,
            approval_id="APR-40", issued_at="2026-11-14T12:00:00Z",
            expires_at="2026-11-14T12:10:00Z",
            nonce=changes.pop("nonce", "nonce-approval-40-0001"),
            timestamp=int(NOW.timestamp()))
        if changes:
            payload = dict(envelope["payload"])
            payload.update(changes)
            envelope = sign_ed25519_request("owner-40", payload, self.private,
                timestamp=int(NOW.timestamp()), nonce="nonce-altered-40-0002")
        return envelope

    def verify(self, envelope=None, **kwargs):
        return verify_sync_bundle_approval(
            envelope=envelope or self.sign(), bundle=self.bundle, owner_id="owner-40",
            registry_path=self.registry, replay_db=self.replay,
            expected_destination="instance-b", now_epoch=int(NOW.timestamp()), now=NOW,
            **kwargs)

    def test_valid_approval_is_bound_to_exact_bundle_and_does_not_import(self):
        result = self.verify()
        self.assertTrue(result["signature_verified"])
        self.assertTrue(result["nonce_replay_protected"])
        self.assertFalse(result["execution_enabled"])
        self.assertFalse(result["import_performed"])
        self.assertEqual(result["event_count"], 1)

    def test_rejects_wrong_digest_destination_scope_and_event_order(self):
        for change in (
            {"bundle_digest": "0" * 64},
            {"destination_instance_id": "instance-c"},
            {"scope": "papi.payment.execute"},
            {"event_ids": ["evt-other"]},
        ):
            with self.subTest(change=change), self.assertRaises(SyncBundleApprovalError):
                self.verify(self.sign(**change))

    def test_rejects_wrong_expected_destination(self):
        with self.assertRaises(SyncBundleApprovalError):
            self.verify(expected_destination="instance-c")

    def test_rejects_expired_and_excessive_approval_ttl(self):
        with self.assertRaises(SyncBundleApprovalError):
            self.verify(self.sign(expires_at="2026-11-14T11:59:59Z"))
        with self.assertRaises(SyncBundleApprovalError):
            self.verify(self.sign(expires_at="2026-11-14T13:00:00Z"))

    def test_replay_is_rejected(self):
        envelope = self.sign()
        self.verify(envelope)
        with self.assertRaises(SyncBundleApprovalError):
            self.verify(envelope)

    def test_rejects_non_owner_signature(self):
        root = Path(self.temp.name)
        other_registry = root / "other.json"
        other_private = provision_ed25519_agent("agent-40", root / "other-keys", other_registry)
        payload = self.sign()["payload"]
        forged = sign_ed25519_request("agent-40", payload, other_private,
            timestamp=int(NOW.timestamp()), nonce="nonce-agent-40-0002")
        with self.assertRaises(SyncBundleApprovalError):
            verify_sync_bundle_approval(
                envelope=forged, bundle=self.bundle, owner_id="owner-40",
                registry_path=other_registry, replay_db=root / "other.sqlite3",
                expected_destination="instance-b", now_epoch=int(NOW.timestamp()), now=NOW)

    def test_rejects_tampered_bundle_and_bad_ttl_policy(self):
        altered = dict(self.bundle)
        altered["export_id"] = "other-export"
        with self.assertRaises(SyncBundleApprovalError):
            self.verify(bundle=altered)
        with self.assertRaises(SyncBundleApprovalError):
            self.verify(max_approval_ttl_seconds=30)


if __name__ == "__main__":
    unittest.main()
