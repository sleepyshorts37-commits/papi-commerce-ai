import copy
import hashlib
import unittest

from papi_core.sync_bundle import SyncBundleError, build_sync_bundle, validate_sync_bundle


def event(sequence=1, event_id="evt-1", record_id="MEM-1", kind="memory"):
    return {"event_id": event_id, "kind": kind, "record_id": record_id,
            "sequence": sequence, "content_digest": hashlib.sha256(b"synthetic").hexdigest()}


class SyncBundleTests(unittest.TestCase):
    def bundle(self, events=None, **kwargs):
        args = dict(source_instance_id="instance-a", destination_instance_id="instance-b",
                    export_id="export-1", created_at="2026-11-14T12:00:00Z",
                    cursor_start=1, cursor_end=1, events=[event()])
        args.update(kwargs)
        if events is not None:
            args["events"] = events
        return build_sync_bundle(**args)

    def test_builds_reference_only_bundle(self):
        bundle = self.bundle()
        self.assertTrue(validate_sync_bundle(bundle, expected_destination="instance-b"))
        self.assertNotIn("content", str(bundle))
        self.assertNotIn("body", str(bundle))

    def test_digest_detects_tampering(self):
        bundle = self.bundle()
        bundle["events"][0]["record_id"] = "MEM-2"
        with self.assertRaises(SyncBundleError):
            validate_sync_bundle(bundle)

    def test_wrong_destination_rejected(self):
        with self.assertRaises(SyncBundleError):
            validate_sync_bundle(self.bundle(), expected_destination="instance-c")

    def test_duplicate_event_id_rejected(self):
        with self.assertRaises(SyncBundleError):
            self.bundle(events=[event(1), event(2, event_id="evt-1", record_id="MEM-2")],
                        cursor_end=2)

    def test_duplicate_resource_rejected(self):
        with self.assertRaises(SyncBundleError):
            self.bundle(events=[event(1), event(2, event_id="evt-2")], cursor_end=2)

    def test_non_monotonic_sequence_rejected(self):
        with self.assertRaises(SyncBundleError):
            self.bundle(events=[event(2), event(1, event_id="evt-2", record_id="MEM-2")],
                        cursor_start=1, cursor_end=2)

    def test_unknown_kind_and_bad_digest_rejected(self):
        bad = event()
        bad["kind"] = "payment"
        with self.assertRaises(SyncBundleError):
            self.bundle(events=[bad])
        bad = event()
        bad["content_digest"] = "not-a-digest"
        with self.assertRaises(SyncBundleError):
            self.bundle(events=[bad])

    def test_timezone_and_cursor_validation(self):
        with self.assertRaises(SyncBundleError):
            self.bundle(created_at="2026-11-14T12:00:00")
        with self.assertRaises(SyncBundleError):
            self.bundle(cursor_start=True)

    def test_empty_bundle_requires_empty_range(self):
        empty = self.bundle(events=[], cursor_start=2, cursor_end=1)
        self.assertTrue(validate_sync_bundle(empty))
        with self.assertRaises(SyncBundleError):
            self.bundle(events=[], cursor_start=1, cursor_end=1)

    def test_version_change_rejected(self):
        bundle = self.bundle()
        bundle["protocol_version"] = "9.0"
        with self.assertRaises(SyncBundleError):
            validate_sync_bundle(bundle)


if __name__ == "__main__":
    unittest.main()
