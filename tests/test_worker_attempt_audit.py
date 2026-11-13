"""Attempt-scoped audit regression tests."""
import json
import tempfile
import threading
import unittest
from unittest.mock import patch
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

    def test_interrupted_append_rolls_back_partial_record(self):
        from papi_core.audit import append_event, new_event
        import os
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            worker = PapiWorker(
                queue=DummyQueue(), registry=object(),
                policy={"execution_enabled": False}, worker_id="worker-a",
                audit_path=path,
            )
            worker._audit(
                job_id="job-interrupt", task_id="task-interrupt",
                attempt_id="00000000-0000-4000-8000-000000000011",
                action="job.claimed", actor="system:worker:worker-a",
                handler="internal.echo", outcome="claimed",
            )
            original = path.read_bytes()
            event = new_event(event_id="interrupted", actor="worker-a", action="job.retry",
                              entity_type="job", entity_id="job-interrupt", details={})
            real_write = os.write
            calls = {"count": 0}
            def partial_then_fail(fd, data):
                calls["count"] += 1
                if calls["count"] == 1:
                    return real_write(fd, data[:7])
                raise OSError("simulated interrupted write")
            with patch("papi_core.audit.os.write", side_effect=partial_then_fail):
                with self.assertRaises(OSError):
                    append_event(event, path)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(len(read_events(path)), 1)

    def test_lock_failure_does_not_append(self):
        import fcntl
        from papi_core.audit import append_event, new_event
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            event = new_event(event_id="lock-failure", actor="worker-a", action="job.retry",
                              entity_type="job", entity_id="job-lock", details={})
            with patch("fcntl.flock", side_effect=OSError("simulated lock failure")):
                with self.assertRaises(OSError):
                    append_event(event, path)
            self.assertEqual(path.read_bytes(), b"")

    def test_read_rejects_valid_json_without_final_newline(self):
        from papi_core.audit import AuditError
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            worker = PapiWorker(
                queue=DummyQueue(), registry=object(),
                policy={"execution_enabled": False}, worker_id="worker-a",
                audit_path=path,
            )
            worker._audit(
                job_id="job-read-tail", task_id="task-read-tail",
                attempt_id="00000000-0000-4000-8000-000000000012",
                action="job.claimed", actor="system:worker:worker-a",
                handler="internal.echo", outcome="claimed",
            )
            path.write_bytes(path.read_bytes().rstrip(b"\n"))
            with self.assertRaises(AuditError):
                read_events(path)

    def test_read_rejects_invalid_utf8(self):
        from papi_core.audit import AuditError
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_bytes(b"\xff\xfe\n")
            with self.assertRaises(AuditError):
                read_events(path)

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
            self.assertEqual(json.loads(confirmed.decode("utf-8").splitlines()[0])["event_id"], "worker:" + __import__("hashlib").sha256("job-tail:00000000-0000-4000-8000-000000000010:job.claimed".encode()).hexdigest())



    def test_failure_result_exposes_actual_queue_retry_state(self):
        class RetryQueue:
            def __init__(self):
                self.kwargs = None

            def fail(self, **kwargs):
                self.kwargs = kwargs
                return "retry"

        with tempfile.TemporaryDirectory() as directory:
            queue = RetryQueue()
            worker = PapiWorker(
                queue=queue, registry=object(),
                policy={"execution_enabled": False}, worker_id="worker-recovery",
                audit_path=Path(directory) / "events.jsonl",
            )
            result = worker._fail_job(
                job_id="job-retry", task_id="task-retry",
                attempt_id="00000000-0000-4000-8000-000000000021",
                lease_token="lease-1", error_code="storage_unavailable",
                status="failed", actor="system:worker:worker-recovery",
                action="job.failed", handler="internal.echo",
                outcome="storage_error", retryable=True,
            )
            self.assertEqual(result["queue_status"], "retry")
            self.assertTrue(queue.kwargs["retryable"])

    def test_terminal_worker_failure_is_sent_as_non_retryable(self):
        class TerminalQueue:
            def __init__(self):
                self.kwargs = None

            def fail(self, **kwargs):
                self.kwargs = kwargs
                return "failed"

        with tempfile.TemporaryDirectory() as directory:
            queue = TerminalQueue()
            worker = PapiWorker(
                queue=queue, registry=object(),
                policy={"execution_enabled": False}, worker_id="worker-recovery",
                audit_path=Path(directory) / "events.jsonl",
            )
            result = worker._fail_job(
                job_id="job-denied", task_id="task-denied",
                attempt_id="00000000-0000-4000-8000-000000000022",
                lease_token="lease-2", error_code="permission_denied",
                status="blocked", actor="system:worker:worker-recovery",
                action="job.blocked", handler="internal.echo",
                outcome="permission_denied", retryable=False,
            )
            self.assertEqual(result["queue_status"], "failed")
            self.assertFalse(queue.kwargs["retryable"])

    def test_process_level_crash_does_not_mark_attempt_failed(self):
        from types import SimpleNamespace
        from papi_core.handler_registry import HandlerRegistry

        class CrashQueue:
            def __init__(self, job):
                self.job = job
                self.store = SimpleNamespace(get_task=lambda task_id: {"task": {
                    "id": task_id, "owner_agent": "agent-crash",
                    "approval_required": False,
                }})
                self.fail_calls = []
                self.complete_calls = []

            def claim(self, *, worker_id):
                return self.job

            def renew(self, **kwargs):
                return True

            def fail(self, **kwargs):
                self.fail_calls.append(kwargs)
                return "retry"

            def complete(self, **kwargs):
                self.complete_calls.append(kwargs)
                return True

        with tempfile.TemporaryDirectory() as directory:
            job = {
                "id": "job-crash", "task_id": "task-crash",
                "handler": "internal.echo", "payload": {},
                "lease_token": "lease-crash",
                "attempt_id": "00000000-0000-4000-8000-000000000023",
                "agent_identity": {"signed": "test"},
            }
            queue = CrashQueue(job)
            registry = HandlerRegistry()
            registry.register("internal.echo", "read_only", lambda payload, context: {"ok": True})
            worker = PapiWorker(
                queue=queue, registry=registry,
                policy={
                    "execution_enabled": True, "external_actions_enabled": False,
                    "allowed_handlers": ["internal.echo"],
                    "action_permissions": {
                        "read_only": {"enabled": True, "owner_approval": False}
                    },
                },
                worker_id="worker-crash",
                audit_path=Path(directory) / "events.jsonl",
            )
            with patch(
                "papi_core.worker.authorize_authenticated_agent",
                return_value={"principal": SimpleNamespace(agent_id="agent-crash")},
            ), patch(
                "papi_core.worker.authorize_job",
            ), patch(
                "papi_core.worker.execute_authorized_job",
                side_effect=SystemExit("simulated process termination"),
            ):
                with self.assertRaises(SystemExit):
                    worker.run_once()
            self.assertEqual(queue.fail_calls, [])
            self.assertEqual(queue.complete_calls, [])

if __name__ == "__main__":
    unittest.main()
