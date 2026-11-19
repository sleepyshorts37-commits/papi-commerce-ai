"""Worker failure-boundary, concurrency and durable-confirmation regressions."""
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from papi_core.audit import read_events
from papi_core.handler_registry import HandlerRegistry
from papi_core.storage import StoreError
from papi_core.worker import PapiWorker


ATTEMPT = "00000000-0000-4000-8000-000000000031"


class FakeStore:
    def __init__(self, task):
        self.task = task
        self.error = None

    def get_task(self, task_id):
        if self.error:
            raise self.error
        return {"task": self.task}


class FakeQueue:
    def __init__(self, job):
        self.job = job
        self.store = FakeStore({
            "id": "task-reliability", "owner_agent": "agent-a", "status": "in_progress",
            "approval_required": False,
        })
        self.lock = threading.Lock()
        self.claim_error = None
        self.renew_result = True
        self.complete_error = None
        self.fail_error = None
        self.fail_calls = []
        self.complete_calls = []
        self.durable_status = "running"

    def claim(self, *, worker_id):
        with self.lock:
            if self.claim_error:
                raise self.claim_error
            if self.job is None:
                return None
            job, self.job = self.job, None
            return dict(job)

    def renew(self, **kwargs):
        return self.renew_result

    def fail(self, **kwargs):
        self.fail_calls.append(kwargs)
        if self.fail_error:
            raise self.fail_error
        self.durable_status = "retry" if len(self.fail_calls) < 2 else "failed"
        return self.durable_status

    def complete(self, **kwargs):
        self.complete_calls.append(kwargs)
        if self.complete_error:
            # Model a server commit followed by a lost response.
            self.durable_status = "completed"
            raise self.complete_error
        self.durable_status = "completed"
        return True


class WorkerReliabilityTests(unittest.TestCase):
    def _job(self):
        return {
            "id": "job-reliability", "task_id": "task-reliability",
            "handler": "internal.echo", "payload": {}, "lease_token": "lease-current",
            "attempt_id": ATTEMPT, "agent_identity": {"signed": "test-envelope"},
        }

    def _worker(self, directory, queue, handler=None, worker_id="worker-reliability"):
        registry = HandlerRegistry()
        registry.register("internal.echo", "read_only", handler or (lambda payload, context: {"ok": True}))
        worker = PapiWorker(
            queue=queue, registry=registry,
            policy={
                "execution_enabled": True, "external_actions_enabled": False,
                "allowed_handlers": ["internal.echo"],
                "action_permissions": {"read_only": {"enabled": True, "owner_approval": False}},
            },
            worker_id=worker_id, audit_path=Path(directory) / f"{worker_id}.jsonl",
        )
        return worker

    def _run_authenticated(self, worker):
        principal = SimpleNamespace(agent_id="agent-a")
        with patch("papi_core.worker.authorize_authenticated_agent", return_value={"principal": principal}), \
             patch("papi_core.worker.authorize_job", return_value=None):
            return worker.run_once()

    def test_concurrent_workers_cannot_claim_the_same_in_memory_reservation(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = FakeQueue(self._job())
            calls = []
            workers = [
                self._worker(directory, queue, lambda payload, context: calls.append(context["worker_id"]) or {"ok": True}, f"worker-{index}")
                for index in range(2)
            ]
            barrier = threading.Barrier(2)
            results = []
            errors = []

            def run(worker):
                try:
                    barrier.wait()
                    results.append(worker.run_once())
                except Exception as exc:
                    errors.append(exc)

            threads = [threading.Thread(target=run, args=(worker,)) for worker in workers]
            with patch("papi_core.worker.authorize_authenticated_agent",
                       return_value={"principal": SimpleNamespace(agent_id="agent-a")}), \
                 patch("papi_core.worker.authorize_job", return_value=None):
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=5)
            self.assertFalse(errors)
            self.assertTrue(all(not thread.is_alive() for thread in threads))
            self.assertEqual(len(calls), 1)
            self.assertEqual(sorted(result["status"] for result in results), ["completed", "idle"])

    def test_claim_network_failure_does_not_start_a_handler(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = FakeQueue(self._job())
            queue.claim_error = StoreError("simulated network loss")
            calls = []
            worker = self._worker(directory, queue, lambda payload, context: calls.append(True) or {})
            result = self._run_authenticated(worker)
            self.assertEqual(result, {"status": "claim_unavailable", "claimed": False})
            self.assertEqual(calls, [])
            self.assertEqual(queue.fail_calls, [])

    def test_crash_before_handler_is_failed_without_handler_started_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = FakeQueue(self._job())
            queue.store.error = StoreError("simulated task read outage")
            calls = []
            worker = self._worker(directory, queue, lambda payload, context: calls.append(True) or {})
            result = self._run_authenticated(worker)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(calls, [])
            self.assertEqual(queue.fail_calls[0]["error_code"], "worker_validation_error")
            actions = [event["action"] for event in read_events(worker.audit_path)]
            self.assertNotIn("job.handler_started", actions)

    def test_lost_lease_before_handler_fences_old_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = FakeQueue(self._job())
            queue.renew_result = False
            calls = []
            worker = self._worker(directory, queue, lambda payload, context: calls.append(True) or {})
            result = self._run_authenticated(worker)
            self.assertEqual(result["status"], "lease_lost")
            self.assertEqual(calls, [])
            self.assertEqual(queue.fail_calls, [])

    def test_handler_crash_records_failure_and_never_reports_success(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = FakeQueue(self._job())

            def crash(payload, context):
                raise RuntimeError("simulated handler crash")

            worker = self._worker(directory, queue, crash)
            result = self._run_authenticated(worker)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(queue.fail_calls[0]["error_code"], "handler_error")
            self.assertEqual(result["queue_status"], "retry")
            self.assertNotEqual(result["status"], "completed")

    def test_lost_complete_response_is_reported_unknown_without_second_transition(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = FakeQueue(self._job())
            queue.complete_error = StoreError("response lost after commit")
            worker = self._worker(directory, queue)
            result = self._run_authenticated(worker)
            self.assertEqual(result["status"], "completion_unknown")
            self.assertEqual(queue.durable_status, "completed")
            self.assertEqual(len(queue.complete_calls), 1)
            self.assertEqual(queue.fail_calls, [])
            actions = [event["action"] for event in read_events(worker.audit_path)]
            self.assertIn("job.completion_unknown", actions)

    def test_failure_transition_network_loss_is_not_reported_as_failed(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = FakeQueue(self._job())
            queue.fail_error = StoreError("simulated fail RPC outage")

            def crash(payload, context):
                raise RuntimeError("simulated handler crash")

            worker = self._worker(directory, queue, crash)
            result = self._run_authenticated(worker)
            self.assertEqual(result["status"], "failure_transition_error")
            self.assertEqual(result["claimed"], True)

    def test_audit_chain_is_readable_after_worker_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            audit_path = Path(directory) / "shared.jsonl"
            first = PapiWorker(queue=FakeQueue(None), registry=HandlerRegistry(),
                               policy={"execution_enabled": False}, worker_id="worker-a",
                               audit_path=audit_path)
            second = PapiWorker(queue=FakeQueue(None), registry=HandlerRegistry(),
                                policy={"execution_enabled": False}, worker_id="worker-b",
                                audit_path=audit_path)
            common = {
                "job_id": "job-restart", "task_id": "task-restart",
                "attempt_id": ATTEMPT, "actor": "system:worker:worker-a",
                "handler": "internal.echo", "outcome": "claimed",
            }
            first._audit(action="job.claimed", **common)
            second._audit(action="job.recovered", **{**common, "actor": "system:worker:worker-b"})
            events = read_events(audit_path)
            self.assertEqual([event["action"] for event in events], ["job.claimed", "job.recovered"])
            self.assertEqual(events[1]["previous_hash"], events[0]["event_hash"])


if __name__ == "__main__":
    unittest.main()
