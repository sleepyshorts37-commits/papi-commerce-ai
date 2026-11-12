import json
import math
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_interrupted_partial_write_fails_closed(self):
        original_write = __import__("os").write
        calls = 0

        def interrupted_write(descriptor, payload):
            nonlocal calls
            calls += 1
            if calls == 1:
                return original_write(descriptor, payload[:12])
            raise OSError("simulated disk write failure")

        with patch("runtime.papi_core.audit.os.write", side_effect=interrupted_write):
            with self.assertRaises(OSError):
                append_event(self.event("evt-partial"), self.path)
        with self.assertRaises(AuditError):
            read_events(self.path)
        with self.assertRaises(AuditError):
            append_event(self.event("evt-after-partial"), self.path)

    @unittest.skipUnless(hasattr(__import__("os"), "O_NOFOLLOW"), "O_NOFOLLOW unavailable")
    def test_journal_symlink_is_rejected(self):
        target = Path(self.temp_dir.name) / "target.jsonl"
        target.write_text("", encoding="utf-8")
        self.path.symlink_to(target)
        with self.assertRaises(OSError):
            append_event(self.event("evt-symlink"), self.path)
        with self.assertRaises(OSError):
            read_events(self.path)
        self.assertEqual(target.read_text(encoding="utf-8"), "")

    @unittest.skipUnless(hasattr(__import__("os"), "mkfifo"), "FIFO unavailable")
    def test_non_regular_journal_path_is_rejected(self):
        fifo_path = Path(self.temp_dir.name) / "audit.fifo"
        __import__("os").mkfifo(fifo_path)
        with self.assertRaises(AuditError):
            read_events(fifo_path)

    @unittest.skipUnless(hasattr(__import__("os"), "O_NOFOLLOW"), "O_NOFOLLOW unavailable")
    def test_lock_symlink_is_rejected(self):
        lock_target = Path(self.temp_dir.name) / "lock-target"
        lock_target.write_text("", encoding="utf-8")
        lock_path = self.path.with_name(self.path.name + ".lock")
        lock_path.symlink_to(lock_target)
        with self.assertRaises(OSError):
            read_events(self.path)
        self.assertEqual(lock_target.read_text(encoding="utf-8"), "")

    def test_world_readable_journal_is_rejected(self):
        append_event(self.event("evt-private"), self.path)
        os.chmod(self.path, 0o644)
        with self.assertRaises(AuditError):
            read_events(self.path)

    def test_world_readable_lock_is_rejected(self):
        read_events(self.path)
        lock_path = self.path.with_name(self.path.name + ".lock")
        os.chmod(lock_path, 0o644)
        with self.assertRaises(AuditError):
            read_events(self.path)

    def test_zero_length_write_fails_instead_of_looping(self):
        with patch("runtime.papi_core.audit.os.write", return_value=0):
            with self.assertRaises(OSError):
                append_event(self.event("evt-zero-write"), self.path)

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
