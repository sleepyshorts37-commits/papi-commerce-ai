import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path

from papi_core.anchor import (
    AnchorClient, AnchorConflict, AnchorError, AnchorIntegrityError,
    AnchorUnavailable, anchor_audit_journal,
)
from papi_core.audit import AuditError, append_event, new_event, read_events


class MemoryAnchorStore:
    """Adaptateur mémoire de test ; ne représente pas un service distant."""

    def __init__(self):
        self.lock = threading.Lock()
        self.head = None
        self.objects = {}
        self.fail_next_cas_after_write = False
        self.fail_next_get = False
        self.fail_next_put_after_write = False

    def get_head(self):
        with self.lock:
            if self.fail_next_get:
                self.fail_next_get = False
                raise OSError("simulated network read failure")
            return self.head

    def get_checkpoint(self, checkpoint_id):
        with self.lock:
            return self.objects.get(checkpoint_id)

    def put_checkpoint(self, checkpoint_id, payload):
        with self.lock:
            existing = self.objects.get(checkpoint_id)
            if existing is not None and existing != payload:
                raise AnchorConflict("immutable key collision")
            self.objects[checkpoint_id] = payload
            if self.fail_next_put_after_write:
                self.fail_next_put_after_write = False
                raise OSError("simulated response loss after durable put")

    def compare_and_swap_head(self, expected, replacement):
        with self.lock:
            if self.head != expected:
                return False
            self.head = replacement
            if self.fail_next_cas_after_write:
                self.fail_next_cas_after_write = False
                raise OSError("simulated response loss after head update")
            return True

    def tamper(self, checkpoint_id, payload):
        with self.lock:
            self.objects[checkpoint_id] = payload

    def delete(self, checkpoint_id):
        with self.lock:
            self.objects.pop(checkpoint_id, None)


def audit_hash(label):
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class AnchorTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryAnchorStore()
        self.client = AnchorClient(self.store)

    def test_anchor_reads_and_verifies_the_local_audit_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "audit.jsonl"
            append_event(new_event(
                event_id="audit-event-1", actor="system", action="worker.test",
                entity_type="job", entity_id="job-1", details={"result": "ok"},
            ), journal)
            checkpoint = anchor_audit_journal(
                self.client, journal, checkpoint_id="journal-checkpoint-1"
            )
            events = read_events(journal)
            self.assertEqual(checkpoint["audit_head"], events[-1]["event_hash"])
            self.assertEqual(checkpoint["sequence"], 1)

    def test_invalid_audit_journal_fails_closed_before_anchor_write(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "audit.jsonl"
            append_event(new_event(
                event_id="audit-event-1", actor="system", action="worker.test",
                entity_type="job", entity_id="job-1", details={"result": "ok"},
            ), journal)
            record = json.loads(journal.read_text(encoding="utf-8"))
            record["action"] = "tampered"
            journal.write_text(json.dumps(record) + chr(10), encoding="utf-8")
            with self.assertRaises(AuditError):
                anchor_audit_journal(self.client, journal, checkpoint_id="must-not-publish")
            self.assertIsNone(self.store.head)

    def test_publish_and_verify_checkpoint_chain(self):
        first = self.client.publish_checkpoint(audit_head=audit_hash("audit-1"), sequence=1, checkpoint_id="checkpoint-1")
        second = self.client.publish_checkpoint(audit_head=audit_hash("audit-2"), sequence=2, checkpoint_id="checkpoint-2")
        self.assertEqual(second["previous_checkpoint_id"], first["checkpoint_id"])
        chain = self.client.verify_chain()
        self.assertEqual([item["checkpoint_id"] for item in chain], ["checkpoint-1", "checkpoint-2"])

    def test_publish_refuses_to_extend_chain_with_missing_ancestor(self):
        self.client.publish_checkpoint(
            audit_head=audit_hash("audit-1"), sequence=1, checkpoint_id="checkpoint-1"
        )
        self.client.publish_checkpoint(
            audit_head=audit_hash("audit-2"), sequence=2, checkpoint_id="checkpoint-2"
        )
        self.store.delete("checkpoint-1")

        with self.assertRaises(AnchorIntegrityError):
            self.client.publish_checkpoint(
                audit_head=audit_hash("audit-3"), sequence=3, checkpoint_id="checkpoint-3"
            )
        self.assertEqual(self.store.head, "checkpoint-2")
        self.assertNotIn("checkpoint-3", self.store.objects)

    def test_idempotent_retry_verifies_all_ancestors(self):
        self.client.publish_checkpoint(
            audit_head=audit_hash("audit-1"), sequence=1, checkpoint_id="checkpoint-1"
        )
        second = self.client.publish_checkpoint(
            audit_head=audit_hash("audit-2"), sequence=2, checkpoint_id="checkpoint-2"
        )
        self.store.delete("checkpoint-1")

        with self.assertRaises(AnchorIntegrityError):
            self.client.publish_checkpoint(
                audit_head=second["audit_head"], sequence=second["sequence"],
                checkpoint_id="checkpoint-2",
            )
        self.assertEqual(self.store.head, "checkpoint-2")

    def test_tampered_checkpoint_is_detected(self):
        checkpoint = self.client.publish_checkpoint(audit_head=audit_hash("audit"), sequence=1, checkpoint_id="checkpoint-1")
        self.store.tamper("checkpoint-1", b'{"checkpoint_id":"checkpoint-1","digest":"00"}')
        with self.assertRaises(AnchorIntegrityError):
            self.client.verify_checkpoint(checkpoint["checkpoint_id"])

    def test_deleted_checkpoint_is_detected(self):
        self.client.publish_checkpoint(audit_head=audit_hash("audit"), sequence=1, checkpoint_id="checkpoint-1")
        self.store.delete("checkpoint-1")
        with self.assertRaises(AnchorIntegrityError):
            self.client.verify_chain()

    def test_rollback_moves_head_without_deleting_later_evidence(self):
        first = self.client.publish_checkpoint(audit_head=audit_hash("audit-1"), sequence=1, checkpoint_id="checkpoint-1")
        second = self.client.publish_checkpoint(audit_head=audit_hash("audit-2"), sequence=2, checkpoint_id="checkpoint-2")
        restored = self.client.rollback(first["checkpoint_id"])
        self.assertEqual(restored["checkpoint_id"], "checkpoint-1")
        self.assertEqual(self.store.head, "checkpoint-1")
        self.assertIn("checkpoint-2", self.store.objects)
        self.assertEqual(len(self.client.verify_chain()), 1)
        self.assertEqual(second["checkpoint_id"], "checkpoint-2")

    def test_rollback_rejects_checkpoint_not_in_current_chain(self):
        self.client.publish_checkpoint(audit_head=audit_hash("audit-1"), sequence=1, checkpoint_id="checkpoint-1")
        self.client.publish_checkpoint(audit_head=audit_hash("audit-2"), sequence=2, checkpoint_id="checkpoint-2")
        self.client.rollback("checkpoint-1")
        with self.assertRaises(AnchorConflict):
            self.client.rollback("checkpoint-2")

    def test_checkpoint_ids_and_head_references_are_validated(self):
        with self.assertRaises(AnchorError):
            self.client.publish_checkpoint(
                audit_head=audit_hash("audit"), sequence=1, checkpoint_id=""
            )
        with self.assertRaises(AnchorIntegrityError):
            self.client.verify_checkpoint("../invalid")
        self.store.head = "../invalid"
        with self.assertRaises(AnchorIntegrityError):
            self.client.verify_chain()

    def test_sequence_must_increase(self):
        self.client.publish_checkpoint(audit_head=audit_hash("audit-1"), sequence=5, checkpoint_id="checkpoint-1")
        with self.assertRaises(AnchorConflict):
            self.client.publish_checkpoint(audit_head=audit_hash("audit-2"), sequence=5, checkpoint_id="checkpoint-2")

    def test_reused_checkpoint_id_cannot_change_content(self):
        self.client.publish_checkpoint(audit_head=audit_hash("audit-1"), sequence=1, checkpoint_id="checkpoint-1")
        with self.assertRaises(AnchorConflict):
            self.client.publish_checkpoint(audit_head=audit_hash("different"), sequence=1, checkpoint_id="checkpoint-1")

    def test_retry_recovers_after_ambiguous_checkpoint_write(self):
        self.store.fail_next_put_after_write = True
        with self.assertRaises(AnchorUnavailable):
            self.client.publish_checkpoint(audit_head=audit_hash("audit"), sequence=1, checkpoint_id="checkpoint-retry")
        recovered = self.client.publish_checkpoint(audit_head=audit_hash("audit"), sequence=1, checkpoint_id="checkpoint-retry")
        self.assertEqual(recovered["checkpoint_id"], "checkpoint-retry")
        self.assertEqual(self.store.head, "checkpoint-retry")

    def test_retry_recovers_after_ambiguous_head_update(self):
        self.store.fail_next_cas_after_write = True
        with self.assertRaises(AnchorUnavailable):
            self.client.publish_checkpoint(audit_head=audit_hash("audit"), sequence=1, checkpoint_id="checkpoint-retry")
        recovered = self.client.publish_checkpoint(audit_head=audit_hash("audit"), sequence=1, checkpoint_id="checkpoint-retry")
        self.assertEqual(recovered["checkpoint_id"], "checkpoint-retry")
        self.assertEqual(self.store.head, "checkpoint-retry")

    def test_network_read_failure_is_not_reported_as_success(self):
        self.store.fail_next_get = True
        with self.assertRaises(AnchorUnavailable):
            self.client.verify_chain()

    def test_concurrent_publishers_cannot_both_advance_same_head(self):
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def publish(identifier):
            try:
                barrier.wait(timeout=3)
                results.append(self.client.publish_checkpoint(
                    audit_head=audit_hash(identifier), sequence=1, checkpoint_id=identifier
                ))
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=publish, args=("checkpoint-a",)),
            threading.Thread(target=publish, args=("checkpoint-b",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], AnchorConflict)
        self.assertEqual(len(self.client.verify_chain()), 1)


    def test_noncanonical_checkpoint_json_with_duplicate_keys_is_rejected(self):
        self.client.publish_checkpoint(
            audit_head=audit_hash("audit"), sequence=1, checkpoint_id="checkpoint-1"
        )
        canonical_payload = self.store.objects["checkpoint-1"]
        self.assertIn(b'\"sequence\":1', canonical_payload)
        ambiguous_payload = canonical_payload.replace(
            b'\"sequence\":1', b'\"sequence\":0,\"sequence\":1', 1
        )
        self.assertNotEqual(ambiguous_payload, canonical_payload)
        self.assertEqual(json.loads(ambiguous_payload), json.loads(canonical_payload))
        self.store.tamper("checkpoint-1", ambiguous_payload)

        with self.assertRaises(AnchorIntegrityError):
            self.client.verify_checkpoint("checkpoint-1")


if __name__ == "__main__":
    unittest.main()
