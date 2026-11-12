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
        self.key = b"test-only-signing-key"
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
        self.assertEqual(key_id, "test-key-1")
        return hmac.new(self.key, payload, hashlib.sha256).hexdigest()

    def verify(self, key_id, payload, signature):
        if key_id != "test-key-1":
            return False
        expected = hmac.new(self.key, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def record(self, previous_digest):
        unsigned = {
            "schema_version": 1,
            "journal_id": self.journal_id,
            "checkpoint": build_checkpoint(self.path),
            "previous_record_digest": previous_digest,
            "key_id": "test-key-1",
        }
        from runtime.papi_core.audit_anchor import _unsigned_payload
        signature = self.sign("test-key-1", _unsigned_payload(unsigned))
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

    def test_same_sequence_publication_is_rejected(self):
        self.add_event("evt-1")
        first_digest = self.publish(self.record(None))
        duplicate = self.record(first_digest)
        with self.assertRaises(CheckpointAnchorError):
            self.publish(duplicate)

    def test_store_record_bytes_are_canonical(self):
        self.add_event("evt-1")
        record = self.record(None)
        self.publish(record)
        digest = self.store.get_latest(self.journal_id)
        stored = self.store.get_record(digest)
        self.assertEqual(stored, canonical_record_bytes(record))
        self.assertEqual(json.loads(stored.decode("utf-8")), record)


if __name__ == "__main__":
    unittest.main()
