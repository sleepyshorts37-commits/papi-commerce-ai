"""Attempt-scoped worker audit and tamper-detection regressions."""
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from papi_core.audit import AuditError, append_event, new_event, read_events
from papi_core.worker import PapiWorker


class DummyQueue:
    pass


class AttemptScopedWorkerAuditTests(unittest.TestCase):
    def _worker(self, directory):
        return PapiWorker(
            queue=DummyQueue(),
            registry=object(),
            policy={"execution_enabled": False},
            worker_id="worker-a",
            audit_path=Path(directory) / "events.jsonl",
        )

    def test_same_job_action_is_recorded_once_per_distinct_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = self._worker(directory)
            common = {
                "job_id": "job-42",
                "task_id": "task-42",
                "action": "job.handler_started",
                "actor": "agent-verified",
                "handler": "internal.echo",
                "outcome": "started",
            }
            worker._audit(attempt_id="00000000-0000-4000-8000-000000000001", **common)
            worker._audit(attempt_id="00000000-0000-4000-8000-000000000002", **common)

            events = read_events(worker.audit_path)
            self.assertEqual(len(events), 2)
            self.assertEqual(
                {event["details"]["attempt_id"] for event in events},
                {
                    "00000000-0000-4000-8000-000000000001",
                    "00000000-0000-4000-8000-000000000002",
                },
            )
            for event in events:
                self.assertEqual(event["details"]["job_id"], "job-42")
                self.assertEqual(event["details"]["task_id"], "task-42")
                self.assertEqual(event["details"]["worker_id"], "worker-a")
                self.assertEqual(event["details"]["agent_id"], "agent-verified")
                self.assertEqual(event["details"]["outcome"], "started")
                self.assertEqual(event["actor"], "agent-verified")
                self.assertEqual(event["action"], "job.handler_started")
                self.assertIn("occurred_at", event)
                self.assertEqual(
                    event["details"]["dedupe_id"],
                    event["event_id"].removeprefix("worker:"),
                )
            self.assertNotEqual(events[0]["event_id"], events[1]["event_id"])

    def test_same_attempt_and_action_is_deduplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = self._worker(directory)
            kwargs = {
                "job_id": "job-42",
                "task_id": "task-42",
                "attempt_id": "00000000-0000-4000-8000-000000000001",
                "action": "job.claimed",
                "actor": "system:worker:worker-a",
                "handler": "internal.echo",
                "outcome": "claimed",
            }
            worker._audit(**kwargs)
            worker._audit(**kwargs)
            events = read_events(worker.audit_path)
            self.assertEqual(len(events), 1)
            self.assertIsNone(events[0]["details"]["agent_id"])

    def test_concurrent_duplicate_appends_are_serialized(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = self._worker(directory)
            kwargs = {
                "job_id": "job-concurrent",
                "task_id": "task-concurrent",
                "attempt_id": "00000000-0000-4000-8000-000000000009",
                "action": "job.handler_started",
                "actor": "agent-verified",
                "handler": "internal.echo",
                "outcome": "started",
            }
            barrier = threading.Barrier(8)
            errors = []

            def append():
                try:
                    barrier.wait()
                    worker._audit(**kwargs)
                except Exception as exc:
                    errors.append(exc)

            threads = [threading.Thread(target=append) for _ in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)
            self.assertFalse(errors)
            self.assertTrue(all(not thread.is_alive() for thread in threads))
            self.assertEqual(len(read_events(worker.audit_path)), 1)

    def test_interrupted_append_rolls_back_partial_record(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = self._worker(directory)
            worker._audit(
                job_id="job-interrupt",
                task_id="task-interrupt",
                attempt_id="00000000-0000-4000-8000-000000000011",
                action="job.claimed",
                actor="system:worker:worker-a",
                handler="internal.echo",
                outcome="claimed",
            )
            original = worker.audit_path.read_bytes()
            event = new_event(
                event_id="interrupted",
                actor="worker-a",
                action="job.retry",
                entity_type="job",
                entity_id="job-interrupt",
                details={},
            )
            real_write = os.write
            calls = {"count": 0}

            def partial_then_fail(fd, data):
                calls["count"] += 1
                if calls["count"] == 1:
                    return real_write(fd, data[:7])
                raise OSError("simulated interrupted write")

            with patch("papi_core.audit.os.write", side_effect=partial_then_fail):
                with self.assertRaises(OSError):
                    append_event(event, worker.audit_path)
            self.assertEqual(worker.audit_path.read_bytes(), original)
            self.assertEqual(len(read_events(worker.audit_path)), 1)

    def test_lock_failure_does_not_append(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            event = new_event(
                event_id="lock-failure",
                actor="worker-a",
                action="job.retry",
                entity_type="job",
                entity_id="job-lock",
                details={},
            )
            with patch("fcntl.flock", side_effect=OSError("simulated lock failure")):
                with self.assertRaises(OSError):
                    append_event(event, path)
            self.assertFalse(path.exists())

    def test_read_rejects_valid_json_without_final_newline(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = self._worker(directory)
            worker._audit(
                job_id="job-read-tail",
                task_id="task-read-tail",
                attempt_id="00000000-0000-4000-8000-000000000012",
                action="job.claimed",
                actor="system:worker:worker-a",
                handler="internal.echo",
                outcome="claimed",
            )
            worker.audit_path.write_bytes(worker.audit_path.read_bytes().rstrip(b"\n"))
            with self.assertRaises(AuditError):
                read_events(worker.audit_path)

    def test_read_rejects_invalid_utf8(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_bytes(b"\xff\xfe\n")
            os.chmod(path, 0o600)
            with self.assertRaises(AuditError):
                read_events(path)

    def test_incomplete_tail_is_rejected_without_losing_confirmed_events(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = self._worker(directory)
            worker._audit(
                job_id="job-tail",
                task_id="task-tail",
                attempt_id="00000000-0000-4000-8000-000000000010",
                action="job.claimed",
                actor="system:worker:worker-a",
                handler="internal.echo",
                outcome="claimed",
            )
            confirmed = worker.audit_path.read_bytes()
            with worker.audit_path.open("ab") as handle:
                handle.write(b'{"event_id":"partial')
            event = new_event(
                event_id="next-event",
                actor="worker-a",
                action="job.retry",
                entity_type="job",
                entity_id="job-tail",
                details={},
            )
            with self.assertRaises(AuditError):
                append_event(event, worker.audit_path)
            self.assertTrue(worker.audit_path.read_bytes().startswith(confirmed))
            with self.assertRaises(AuditError):
                read_events(worker.audit_path)

    def test_hash_chain_detects_modified_event(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = self._worker(directory)
            worker._audit(
                job_id="job-tamper",
                task_id="task-tamper",
                attempt_id="00000000-0000-4000-8000-000000000013",
                action="job.claimed",
                actor="system:worker:worker-a",
                handler="internal.echo",
                outcome="claimed",
            )
            record = json.loads(worker.audit_path.read_text(encoding="utf-8"))
            record["details"]["outcome"] = "tampered"
            worker.audit_path.write_text(
                json.dumps(record, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(AuditError):
                read_events(worker.audit_path)


    def test_read_rejects_duplicate_json_keys_at_all_nesting_levels(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            event = new_event(
                event_id="duplicate-json-key",
                actor="worker-a",
                action="job.retry",
                entity_type="job",
                entity_id="job-duplicate-json",
                details={"result": "ok"},
            )
            append_event(event, path)
            original = path.read_bytes()
            duplicate_cases = (
                (
                    b'"action": "job.retry"',
                    b'"action": "tampered", "action": "job.retry"',
                ),
                (
                    b'"result": "ok"',
                    b'"result": "tampered", "result": "ok"',
                ),
            )
            for needle, replacement in duplicate_cases:
                with self.subTest(needle=needle):
                    ambiguous = original.replace(needle, replacement, 1)
                    self.assertNotEqual(ambiguous, original)
                    # The default JSON decoder keeps the final value, so the
                    # decoded object and its event hash still appear unchanged.
                    self.assertEqual(json.loads(ambiguous), json.loads(original))
                    path.write_bytes(ambiguous)
                    with self.assertRaises(AuditError):
                        read_events(path)


    def test_read_rejects_journal_over_byte_limit_before_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_bytes(b"123456789")
            os.chmod(path, 0o600)
            with patch("papi_core.audit.MAX_JOURNAL_BYTES", 8):
                with self.assertRaises(AuditError):
                    read_events(path)

    def test_read_rejects_oversized_raw_line_even_when_event_is_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            append_event(
                new_event(
                    event_id="oversized-line",
                    actor="worker-a",
                    action="job.retry",
                    entity_type="job",
                    entity_id="job-oversized-line",
                    details={"result": "ok"},
                ),
                path,
            )
            original = path.read_bytes()
            oversized = original[:-1] + (b" " * 64) + b"\\n"
            path.write_bytes(oversized)
            with patch("papi_core.audit.MAX_AUDIT_LINE_BYTES", len(original) - 1):
                with self.assertRaises(AuditError):
                    read_events(path)

    def test_read_rejects_nonstandard_json_constants(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            append_event(
                new_event(
                    event_id="nonstandard-constant",
                    actor="worker-a",
                    action="job.retry",
                    entity_type="job",
                    entity_id="job-nonstandard",
                    details={"result": "ok"},
                ),
                path,
            )
            original = path.read_bytes()
            for constant in (b"NaN", b"Infinity", b"-Infinity"):
                with self.subTest(constant=constant):
                    ambiguous = original.replace(b'"result": "ok"', b'"result": ' + constant, 1)
                    self.assertNotEqual(ambiguous, original)
                    path.write_bytes(ambiguous)
                    with self.assertRaises(AuditError):
                        read_events(path)
            path.write_bytes(original)

    def test_read_rejects_too_many_events(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            append_event(
                new_event(
                    event_id="event-count-limit",
                    actor="worker-a",
                    action="job.retry",
                    entity_type="job",
                    entity_id="job-count-limit",
                    details={},
                ),
                path,
            )
            with patch("papi_core.audit.MAX_AUDIT_EVENTS", 0):
                with self.assertRaises(AuditError):
                    read_events(path)



if __name__ == "__main__":
    unittest.main()
