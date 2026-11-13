"""Attempt-scoped audit regression tests."""
import tempfile
import threading
import unittest
from pathlib import Path

from papi_core.audit import read_events
from papi_core.worker import PapiWorker


class DummyQueue:
    pass


class AttemptScopedWorkerAuditTests(unittest.TestCase):
    def test_same_job_action_is_recorded_once_per_distinct_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = PapiWorker(
                queue=DummyQueue(), registry=object(),
                policy={"execution_enabled": False}, worker_id="worker-a",
                audit_path=Path(directory) / "events.jsonl",
            )
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
                self.assertEqual(event["actor"], "agent-verified")
                self.assertEqual(event["details"]["agent_id"], "agent-verified")
                self.assertEqual(event["details"]["dedupe_id"], event["event_id"].removeprefix("worker:"))
            self.assertNotEqual(events[0]["event_id"], events[1]["event_id"])

    def test_same_attempt_and_action_is_deduplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = PapiWorker(
                queue=DummyQueue(), registry=object(),
                policy={"execution_enabled": False}, worker_id="worker-a",
                audit_path=Path(directory) / "events.jsonl",
            )
            kwargs = {
                "job_id": "job-42", "task_id": "task-42",
                "attempt_id": "00000000-0000-4000-8000-000000000001",
                "action": "job.claimed", "actor": "system:worker:worker-a",
                "handler": "internal.echo", "outcome": "claimed",
            }
            worker._audit(**kwargs)
            worker._audit(**kwargs)
            self.assertEqual(len(read_events(worker.audit_path)), 1)

    def test_concurrent_duplicate_appends_are_serialized(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = PapiWorker(
                queue=DummyQueue(), registry=object(),
                policy={"execution_enabled": False}, worker_id="worker-a",
                audit_path=Path(directory) / "events.jsonl",
            )
            kwargs = {
                "job_id": "job-concurrent", "task_id": "task-concurrent",
                "attempt_id": "00000000-0000-4000-8000-000000000009",
                "action": "job.handler_started", "actor": "agent-verified",
                "handler": "internal.echo", "outcome": "started",
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

    def test_incomplete_tail_is_rejected_without_losing_confirmed_events(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            worker = PapiWorker(
                queue=DummyQueue(), registry=object(),
                policy={"execution_enabled": False}, worker_id="worker-a",
                audit_path=path,
            )
            common = {
                "job_id": "job-tail", "task_id": "task-tail",
                "attempt_id": "00000000-0000-4000-8000-000000000010",
                "action": "job.claimed", "actor": "system:worker:worker-a",
                "handler": "internal.echo", "outcome": "claimed",
            }
            worker._audit(**common)
            confirmed = path.read_bytes()
            with path.open("ab") as handle:
                handle.write(b'{"event_id":"partial')
            from papi_core.audit import AuditError, append_event, new_event
            event = new_event(event_id="next-event", actor="worker-a", action="job.retry",
                              entity_type="job", entity_id="job-tail", details={})
            with self.assertRaises(AuditError):
                append_event(event, path)
            self.assertTrue(path.read_bytes().startswith(confirmed))
            self.assertEqual(len(read_events(Path(directory) / "confirmed.jsonl")), 0)


if __name__ == "__main__":
    unittest.main()
