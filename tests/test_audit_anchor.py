import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path

from runtime.papi_core.audit import append_event, new_event
from runtime.papi_core.audit_checkpoint import build_checkpoint
from runtime.papi_core.audit_anchor import (
    CheckpointAnchorError,
    CheckpointConflict,
    canonical_record_bytes,
    publish_checkpoint_record,
    verify_checkpoint_anchor,
)


class FakeCheckpointStore:
    """In-memory contract fake; not evidence of external durability."""

    def __init__(self):
        self.records = {}
        self.latest = {}
        self.force_conflict = False

    def get_latest(self, journal_id):
        return self.latest.get(journal_id)

    def get_record(self, record_digest):
        return self.records.get(record_digest)

    def put_record(self, record_digest, canonical_record):
        existing = self.records.get(record_digest)
        if existing is not None and existing != canonical_record:
            raise AssertionError("immutable record mutation")
        self.records[record_digest] = canonical_record

    def compare_and_swap_latest(self, journal_id, expected_digest, new_digest):
        if self.force_conflict or self.latest.get(journal_id) != expected_digest:
            return False
        if new_digest not in self.records:
            return False
        self.latest[journal_id] = new_digest
        return True


class AuditAnchorContractTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "audit.jsonl"
        self.store = FakeCheckpointStore()
        self.keys = {
            "test-key-1": b"test-only-signing-key",
            "test-key-2": b"rotated-test-only-signing-key",
        }
        self.journal_id = "test-journal-01"

    def tearDown(self):
        self.temp_dir.cleanup()

    def add_event(self, event_id):
        event = new_event(
            event_id=event_id, actor="system:test", action="test.event",
            entity_type="test", entity_id=event_id, details={"ok": True},
        )
        append_event(event, self.path)

    def sign(self, key_id, payload):
        key = self.keys[key_id]
        return hmac.new(key, payload, hashlib.sha256).hexdigest()

    def verify(self, key_id, payload, signature):
        key = self.keys.get(key_id)
        if key is None:
            return False
        expected = hmac.new(key, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def record(self, previous_digest, key_id="test-key-1"):
        unsigned = {
            "schema_version": 1,
            "journal_id": self.journal_id,
            "checkpoint": build_checkpoint(self.path),
            "previous_record_digest": previous_digest,
            "key_id": key_id,
        }
        from runtime.papi_core.audit_anchor import _unsigned_payload
        signature = self.sign(key_id, _unsigned_payload(unsigned))
        return {**unsigned, "signature": signature}

    def publish(self, record):
        return publish_checkpoint_record(
            journal_path=self.path,
            journal_id=self.journal_id,
            record=record,
            store=self.store,
            verify_signature=self.verify,
        )

    def test_first_publication_from_genesis(self):
        self.add_event("evt-1")
        digest = self.publish(self.record(None))
        self.assertEqual(self.store.get_latest(self.journal_id), digest)
        self.assertIn(digest, self.store.records)

    def test_key_rotation_preserves_old_signatures_and_accepts_new_key(self):
        self.add_event("evt-1")
        first_digest = self.publish(self.record(None, key_id="test-key-1"))
        self.add_event("evt-2")
        second_digest = self.publish(
            self.record(first_digest, key_id="test-key-2")
        )
        self.assertNotEqual(first_digest, second_digest)
        self.assertEqual(self.store.get_latest(self.journal_id), second_digest)
        # Publishing the successor verifies the predecessor with its historical key.
        self.assertTrue(self.verify("test-key-1", b"probe", self.sign("test-key-1", b"probe")))
        self.assertTrue(self.verify("test-key-2", b"probe", self.sign("test-key-2", b"probe")))

    def test_unknown_key_id_is_rejected_before_storage(self):
        self.add_event("evt-1")
        unsigned = {
            "schema_version": 1,
            "journal_id": self.journal_id,
            "checkpoint": build_checkpoint(self.path),
            "previous_record_digest": None,
            "key_id": "retired-or-unknown-key",
        }
        from runtime.papi_core.audit_anchor import _unsigned_payload
        record = {
            **unsigned,
            "signature": hmac.new(
                b"unknown-key", _unsigned_payload(unsigned), hashlib.sha256
            ).hexdigest(),
        }
        with self.assertRaises(CheckpointAnchorError):
            self.publish(record)
        self.assertEqual(self.store.records, {})

    def test_forward_publication_requires_anchored_prefix(self):
        self.add_event("evt-1")
        first_digest = self.publish(self.record(None))
        self.add_event("evt-2")
        second_digest = self.publish(self.record(first_digest))
        self.assertNotEqual(first_digest, second_digest)
        self.assertEqual(self.store.get_latest(self.journal_id), second_digest)

    def test_rewritten_or_rolled_back_anchored_prefix_is_rejected(self):
        self.add_event("evt-1")
        first_digest = self.publish(self.record(None))
        self.add_event("evt-2")
        # Replace local history with an empty journal after an anchor exists.
        self.path.write_text("", encoding="utf-8")
        with self.assertRaises(CheckpointAnchorError):
            self.publish(self.record(first_digest))

    def test_invalid_signature_is_rejected_before_storage(self):
        self.add_event("evt-1")
        record = self.record(None)
        record["signature"] = "00" * 32
        with self.assertRaises(CheckpointAnchorError):
            self.publish(record)
        self.assertEqual(self.store.records, {})

    def test_record_cannot_be_replayed_for_another_journal(self):
        self.add_event("evt-1")
        record = self.record(None)
        with self.assertRaises(CheckpointAnchorError):
            publish_checkpoint_record(
                journal_path=self.path, journal_id="other-journal",
                record=record, store=self.store, verify_signature=self.verify,
            )

    def test_cas_conflict_does_not_advance_latest(self):
        self.add_event("evt-1")
        record = self.record(None)
        self.store.force_conflict = True
        with self.assertRaises(CheckpointConflict):
            self.publish(record)
        self.assertIsNone(self.store.get_latest(self.journal_id))
        # Immutable candidate may exist after an uncertain CAS; retry is safe.
        self.assertEqual(len(self.store.records), 1)

    def test_retry_after_timeout_after_commit_returns_existing_digest(self):
        self.add_event("evt-1")
        record = self.record(None)
        original_cas = self.store.compare_and_swap_latest
        calls = {"count": 0}
        def commit_then_timeout(journal_id, expected_digest, new_digest):
            result = original_cas(journal_id, expected_digest, new_digest)
            calls["count"] += 1
            if calls["count"] == 1 and result:
                raise TimeoutError("response lost after commit")
            return result
        self.store.compare_and_swap_latest = commit_then_timeout
        with self.assertRaises(TimeoutError):
            self.publish(record)
        committed_digest = self.store.get_latest(self.journal_id)
        self.assertIsNotNone(committed_digest)
        recovered_digest = self.publish(record)
        self.assertEqual(recovered_digest, committed_digest)
        self.assertEqual(self.store.get_latest(self.journal_id), committed_digest)
        self.assertEqual(len(self.store.records), 1)
    def test_same_sequence_publication_is_rejected(self):
        self.add_event("evt-1")
        first_digest = self.publish(self.record(None))
        duplicate = self.record(first_digest)
        with self.assertRaises(CheckpointAnchorError):
            self.publish(duplicate)

    def test_tampered_predecessor_bytes_are_rejected(self):
        self.add_event("evt-1")
        digest = self.publish(self.record(None))
        self.store.records[digest] = self.store.records[digest] + b" "
        self.add_event("evt-2")
        with self.assertRaises(CheckpointAnchorError):
            self.publish(self.record(digest))

    def test_noncanonical_predecessor_encoding_is_rejected(self):
        self.add_event("evt-1")
        digest = self.publish(self.record(None))
        decoded = json.loads(self.store.records[digest].decode("utf-8"))
        self.store.records[digest] = json.dumps(decoded, indent=2).encode("utf-8")
        self.add_event("evt-2")
        with self.assertRaises(CheckpointAnchorError):
            self.publish(self.record(digest))

    def test_competing_publisher_cannot_overwrite_latest_pointer(self):
        self.add_event("evt-1")
        record = self.record(None)
        competing_digest = "a" * 64
        original_cas = self.store.compare_and_swap_latest
        def competing_cas(journal_id, expected_digest, new_digest):
            self.store.latest[journal_id] = competing_digest
            return original_cas(journal_id, expected_digest, new_digest)
        self.store.compare_and_swap_latest = competing_cas
        with self.assertRaises(CheckpointConflict):
            self.publish(record)
        self.assertEqual(self.store.get_latest(self.journal_id), competing_digest)


    def test_read_only_verifier_reports_genesis_as_unanchored(self):
        self.add_event("evt-1")
        result = verify_checkpoint_anchor(
            journal_path=self.path, journal_id=self.journal_id,
            store=self.store, verify_signature=self.verify,
        )
        self.assertFalse(result["anchored"])
        self.assertIsNone(result["latest_digest"])
        self.assertEqual(result["unanchored_suffix"], 1)

    def test_read_only_verifier_checks_full_chain_and_reports_suffix(self):
        self.add_event("evt-1")
        first_digest = self.publish(self.record(None, key_id="test-key-1"))
        self.add_event("evt-2")
        second_digest = self.publish(
            self.record(first_digest, key_id="test-key-2")
        )
        self.add_event("evt-3")
        result = verify_checkpoint_anchor(
            journal_path=self.path, journal_id=self.journal_id,
            store=self.store, verify_signature=self.verify,
        )
        self.assertTrue(result["anchored"])
        self.assertEqual(result["latest_digest"], second_digest)
        self.assertEqual(result["checkpoint"]["sequence"], 2)
        self.assertEqual(result["unanchored_suffix"], 1)

    def test_read_only_verifier_rejects_local_rollback(self):
        self.add_event("evt-1")
        self.publish(self.record(None))
        self.path.write_text("", encoding="utf-8")
        with self.assertRaises(CheckpointAnchorError):
            verify_checkpoint_anchor(
                journal_path=self.path, journal_id=self.journal_id,
                store=self.store, verify_signature=self.verify,
            )

    def test_read_only_verifier_rejects_tampered_external_record(self):
        self.add_event("evt-1")
        digest = self.publish(self.record(None))
        self.store.records[digest] += b" "
        with self.assertRaises(CheckpointAnchorError):
            verify_checkpoint_anchor(
                journal_path=self.path, journal_id=self.journal_id,
                store=self.store, verify_signature=self.verify,
            )

    def test_store_record_bytes_are_canonical(self):
        self.add_event("evt-1")
        record = self.record(None)
        self.publish(record)
        digest = self.store.get_latest(self.journal_id)
        stored = self.store.get_record(digest)
        self.assertEqual(stored, canonical_record_bytes(record))
        self.assertEqual(json.loads(stored.decode("utf-8")), record)


    def test_read_only_verifier_rejects_signed_broken_predecessor_link(self):
        self.add_event("evt-1")
        record = self.record(None)
        record["previous_record_digest"] = "b" * 64
        from runtime.papi_core.audit_anchor import _unsigned_payload
        record["signature"] = self.sign("test-key-1", _unsigned_payload(record))
        raw = canonical_record_bytes(record)
        digest = hashlib.sha256(raw).hexdigest()
        self.store.records[digest] = raw
        self.store.latest[self.journal_id] = digest
        with self.assertRaises(CheckpointAnchorError):
            verify_checkpoint_anchor(
                journal_path=self.path, journal_id=self.journal_id,
                store=self.store, verify_signature=self.verify,
            )

    def test_read_only_verifier_rejects_malformed_signed_checkpoint(self):
        self.add_event("evt-1")
        record = self.record(None)
        record["checkpoint"]["sequence"] = True
        from runtime.papi_core.audit_anchor import _unsigned_payload
        record["signature"] = self.sign("test-key-1", _unsigned_payload(record))
        raw = canonical_record_bytes(record)
        digest = hashlib.sha256(raw).hexdigest()
        self.store.records[digest] = raw
        self.store.latest[self.journal_id] = digest
        with self.assertRaises(CheckpointAnchorError):
            verify_checkpoint_anchor(
                journal_path=self.path, journal_id=self.journal_id,
                store=self.store, verify_signature=self.verify,
            )


    def test_read_only_verifier_rejects_retired_historical_signature(self):
        self.add_event("evt-1")
        first_digest = self.publish(self.record(None, key_id="test-key-1"))
        self.add_event("evt-2")
        self.publish(self.record(first_digest, key_id="test-key-2"))

        def verifier_without_retired_key(key_id, payload, signature):
            if key_id == "test-key-1":
                return False
            return self.verify(key_id, payload, signature)

        with self.assertRaises(CheckpointAnchorError):
            verify_checkpoint_anchor(
                journal_path=self.path, journal_id=self.journal_id,
                store=self.store, verify_signature=verifier_without_retired_key,
            )




if __name__ == "__main__":
    unittest.main()
