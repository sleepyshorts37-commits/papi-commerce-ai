"""Attempt-scoped audit regression tests."""
import tempfile
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


if __name__ == "__main__":
    unittest.main()
