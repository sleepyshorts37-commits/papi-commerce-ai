import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from papi_core.sync_transfer_manifest import (
    SyncTransferManifestError, build_sync_transfer_manifest,
    validate_sync_transfer_manifest,
)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def write_object(directory, suffix, body, digest_field):
    digest = hashlib.sha256(canonical(body)).hexdigest()
    value = {**body, digest_field: digest}
    path = directory / (digest + suffix)
    path.write_bytes(canonical(value))
    return path


class SyncTransferManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        bundle = {
            "bundle_digest": "a" * 64,
            "source_instance_id": "instance-source",
            "destination_instance_id": "instance-target",
            "export_id": "export-53",
        }
        approval = {"payload": {"destination_instance_id": "instance-target"}}
        package_body = {"format_version": 1, "bundle": bundle, "approval": approval}
        self.package = write_object(self.root, ".papisync", package_body, "package_digest")
        payload_body = {"format_version": 1, "bundle_digest": "a" * 64, "records": []}
        self.payload = write_object(self.root, ".papidata", payload_body, "payload_digest")

    def tearDown(self):
        self.temp.cleanup()

    def test_build_and_validate_manifest(self):
        manifest = build_sync_transfer_manifest(
            package_path=self.package, payload_path=self.payload)
        self.assertTrue(validate_sync_transfer_manifest(manifest))
        self.assertEqual(manifest["source_instance_id"], "instance-source")
        self.assertEqual(manifest["destination_instance_id"], "instance-target")
        self.assertFalse(manifest["network_transfer_performed"])
        self.assertFalse(manifest["import_performed"])
        self.assertFalse(manifest["execution_enabled"])

    def test_tampered_file_is_rejected(self):
        self.package.write_bytes(self.package.read_bytes() + b" ")
        with self.assertRaises(SyncTransferManifestError):
            build_sync_transfer_manifest(package_path=self.package, payload_path=self.payload)

    def test_payload_for_another_bundle_is_rejected(self):
        payload_body = {"format_version": 1, "bundle_digest": "b" * 64, "records": []}
        other = write_object(self.root, ".papidata", payload_body, "payload_digest")
        with self.assertRaises(SyncTransferManifestError):
            build_sync_transfer_manifest(package_path=self.package, payload_path=other)

    def test_destination_mismatch_in_approval_is_rejected(self):
        body = {"format_version": 1,
                "bundle": {"bundle_digest": "a" * 64, "source_instance_id": "instance-source",
                           "destination_instance_id": "instance-target", "export_id": "export-53"},
                "approval": {"payload": {"destination_instance_id": "instance-other"}}}
        other = write_object(self.root, ".papisync", body, "package_digest")
        with self.assertRaises(SyncTransferManifestError):
            build_sync_transfer_manifest(package_path=other, payload_path=self.payload)

    def test_symlink_is_rejected(self):
        link = self.root / ("c" * 64 + ".papisync")
        link.symlink_to(self.package)
        with self.assertRaises(SyncTransferManifestError):
            build_sync_transfer_manifest(package_path=link, payload_path=self.payload)

    def test_manifest_tampering_is_rejected(self):
        manifest = build_sync_transfer_manifest(
            package_path=self.package, payload_path=self.payload)
        manifest["destination_instance_id"] = "instance-attacker"
        with self.assertRaises(SyncTransferManifestError):
            validate_sync_transfer_manifest(manifest)

    def test_execution_flags_cannot_be_enabled(self):
        manifest = build_sync_transfer_manifest(
            package_path=self.package, payload_path=self.payload)
        manifest["network_transfer_performed"] = True
        with self.assertRaises(SyncTransferManifestError):
            validate_sync_transfer_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
