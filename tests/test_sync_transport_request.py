import base64
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
from papi_core.sync_transport_request import (
    SyncTransportPlanError, build_sync_transport_request,
)

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)

class SyncTransportRequestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = self.root / "public.json"
        self.private = provision_ed25519_agent("owner-56", self.root / "keys", self.registry)
        bundle = build_sync_bundle(
            source_instance_id="source-56", destination_instance_id="target-56",
            export_id="export-56", created_at="2026-11-14T11:59:00Z",
            cursor_start=1, cursor_end=0, events=[],
        )
        approval = sign_sync_bundle_approval(
            owner_id="owner-56", private_key_path=self.private, bundle=bundle,
            approval_id="APR-56", issued_at="2026-11-14T12:00:00Z",
            expires_at="2026-11-14T12:10:00Z",
            nonce="nonce-transport-56-0001", timestamp=int(NOW.timestamp()),
        )
        package = write_sync_package(bundle=bundle, approval=approval, spool_dir=self.root)
        payload = write_sync_payload(bundle=bundle, records=[], spool_dir=self.root)
        self.package_path = Path(package["path"])
        self.payload_path = Path(payload["path"])
        self.manifest = build_sync_transfer_manifest(
            package_path=self.package_path, payload_path=self.payload_path)

    def tearDown(self):
        self.temp.cleanup()

    def build(self, endpoint="https://sync.example.com/v1/receive", hosts=("sync.example.com",)):
        return build_sync_transport_request(
            manifest=self.manifest, directory=self.root,
            endpoint=endpoint, allowed_hosts=hosts)

    def test_builds_deterministic_post_without_network_side_effects(self):
        first = self.build()
        second = self.build()
        self.assertEqual(first["body_sha256"], second["body_sha256"])
        self.assertEqual(first["method"], "POST")
        self.assertEqual(first["headers"]["Idempotency-Key"], self.manifest["delivery_id"])
        self.assertEqual(base64.b64decode(first["body"]["package_base64"]), self.package_path.read_bytes())
        self.assertEqual(base64.b64decode(first["body"]["payload_base64"]), self.payload_path.read_bytes())
        self.assertFalse(first["network_transfer_performed"])
        self.assertFalse(first["nonce_consumed"])
        self.assertFalse(first["receipt_committed"])
        self.assertTrue(first["receiver_reverification_required"])

    def test_rejects_http_and_unlisted_host(self):
        for url, hosts in (("http://sync.example.com/receive", ("sync.example.com",)),
                           ("https://evil.example/receive", ("sync.example.com",))):
            with self.assertRaises(SyncTransportPlanError):
                self.build(url, hosts)

    def test_rejects_local_and_private_ip(self):
        for url in ("https://127.0.0.1/receive", "https://192.168.1.10/receive",
                    "https://localhost/receive"):
            with self.assertRaises(SyncTransportPlanError):
                self.build(url, ("localhost", "127.0.0.1", "192.168.1.10"))

    def test_rejects_credentials_query_fragment_and_nonstandard_port(self):
        for url in ("https://user@sync.example.com/receive",
                    "https://sync.example.com/receive?token=x",
                    "https://sync.example.com/receive#fragment",
                    "https://sync.example.com:8443/receive"):
            with self.assertRaises(SyncTransportPlanError):
                self.build(url)

    def test_rejects_modified_staged_files(self):
        self.package_path.write_bytes(self.package_path.read_bytes() + b"x")
        with self.assertRaises(SyncTransportPlanError):
            self.build()

if __name__ == "__main__":
    unittest.main()
