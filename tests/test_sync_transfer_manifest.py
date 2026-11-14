import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from papi_core.sync_bundle import build_sync_bundle
from papi_core.sync_payload import build_sync_payload
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
        bundle = build_sync_bundle(
            source_instance_id="instance-source",
            destination_instance_id="instance-target",
            export_id="export-53",
            created_at="2026-11-14T10:00:00Z",
            cursor_start=1, cursor_end=0, events=[],
        )
        approval = {"payload": {"destination_instance_id": "instance-target"}}
        package_body = {"format_version": 1, "bundle": bundle, "approval": approval}
        self.package = write_object(self.root, ".papisync", package_body, "package_digest")
        payload = build_sync_payload(bundle=bundle, records=[])
        payload_body = {key: payload[key] for key in ("format_version", "bundle_digest", "records")}
        self.payload = write_object(self.root, ".papidata", payload_body, "payload_digest")
