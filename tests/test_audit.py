import json
import math
import tempfile
import threading
import unittest
from pathlib import Path

from runtime.papi_core.audit import AuditError, append_event, new_event, read_events, _journal_lock


class AuditHashChainTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "audit.jsonl"

    def tearDown(self):
        self.temp_dir.cleanup()

    def event(self, event_id, action="task.updated"):
        return new_event(
            event_id=event_id, actor="agent-01", action=action,
            entity_type="task", entity_id="task-01",
            details={"status": "review"},
        )

    def test_appends_and_verifies_linked_events(self):
        self.assertTrue(append_event(self.event("evt-1"), self.path))
        self.assertTrue(append_event(self.event("evt-2"), self.path))
        events = read_events(self.path)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[1]["previous_hash"], events[0]["event_hash"])

    def test_duplicate_event_id_is_idempotent(self):
        event = self.event("evt-1")
        self.assertTrue(append_event(event, self.path))
        self.assertFalse(append_event(event, self.path))
        self.assertEqual(len(read_events(self.path)), 1)

    def test_modified_event_is_detected(self):
        append_event(self.event("evt-1"), self.path)
        record = json.loads(self.path.read_text(encoding="utf-8"))
        record["details"]["status"] = "tampered"
        self.path.write_text(json.dumps(record) + "\n", encoding="utf-8")
        with self.assertRaises(AuditError):
            read_events(self.path)

    def test_truncated_final_record_fails_closed(self):
        append_event(self.event("evt-1"), self.path)
        with self.path.open("ab") as journal:
            journal.write(b'{"event_id":"partial')
            journal.flush()
        with self.assertRaises(AuditError):
            read_events(self.path)
        with self.assertRaises(AuditError):
            append_event(self.event("evt-2"), self.path)

    def test_removed_middle_event_is_detected(self):
        append_event(self.event("evt-1"), self.path)
        append_event(self.event("evt-2"), self.path)
        append_event(self.event("evt-3"), self.path)
        records = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]
        self.path.write_text(
            json.dumps(records[0]) + "\n" + json.dumps(records[2]) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(AuditError):
            read_events(self.path)

    def test_non_finite_numbers_are_rejected(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                event = self.event("non-finite")
                event["details"]["amount"] = value
                with self.assertRaises(AuditError):
                    append_event(event, self.path)

    def test_naive_timestamp_is_rejected(self):
        event = self.event("naive-time")
        event["occurred_at"] = "2026-11-12T10:30:00"
        with self.assertRaises(AuditError):
            append_event(event, self.path)

    def test_timezone_aware_timestamp_is_accepted(self):
        event = self.event("aware-time")
        event["occurred_at"] = "2026-11-12T10:30:00+00:00"
        self.assertTrue(append_event(event, self.path))
        self.assertEqual(len(read_events(self.path)), 1)

    def test_read_waits_for_an_active_append_lock(self):
        append_event(self.event("evt-1"), self.path)
        started = threading.Event()
        finished = threading.Event()

        def reader():
            started.set()
            read_events(self.path)
            finished.set()

        with _journal_lock(self.path):
            thread = threading.Thread(target=reader)
            thread.start()
            self.assertTrue(started.wait(timeout=2))
            self.assertFalse(finished.wait(timeout=0.1))

        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertTrue(finished.is_set())

    def test_legacy_unlinked_journal_fails_closed(self):
        self.path.write_text(json.dumps(self.event("legacy")) + "\n", encoding="utf-8")
        with self.assertRaises(AuditError):
            read_events(self.path)
        with self.assertRaises(AuditError):
            append_event(self.event("new"), self.path)


if __name__ == "__main__":
    unittest.main()
