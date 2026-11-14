import unittest
from unittest.mock import patch
import tempfile
from pathlib import Path

from papi_core.handler_registry import HandlerRegistry
from papi_core.worker import PapiWorker, WorkerError


class QueueSpy:
    def __init__(self, claim_result=None):
        self.claim_result = claim_result
        self.claim_calls = 0
        self.fail_calls = []

    def claim(self, *, worker_id):
        self.claim_calls += 1
        return self.claim_result

    def fail(self, **kwargs):
        self.fail_calls.append(kwargs)
        return "failed"

    def complete(self, **kwargs):
        raise AssertionError("Un job non authentifié ne doit jamais être complété.")


class FakeStore:
    def get_task(self, task_id):
        return {"task": {"id": task_id, "owner_agent": "agent-a", "status": "in_progress",
                         "approval_required": False}}


class WorkerSafetyTests(unittest.TestCase):
    def test_disabled_worker_does_not_claim_a_job(self):
        queue = QueueSpy()
        worker = PapiWorker(queue=queue, registry=HandlerRegistry(),
            policy={"execution_enabled": False}, worker_id="worker-test")
        result = worker.run_once()
        self.assertEqual(result, {"status": "disabled", "claimed": False})
        self.assertEqual(queue.claim_calls, 0)

    def test_enabled_worker_with_empty_queue_returns_idle(self):
        queue = QueueSpy()
        worker = PapiWorker(queue=queue, registry=HandlerRegistry(),
            policy={"execution_enabled": True}, worker_id="worker-test")
        result = worker.run_once()
        self.assertEqual(result, {"status": "idle", "claimed": False})
        self.assertEqual(queue.claim_calls, 1)

    def test_blank_worker_id_is_rejected(self):
        with self.assertRaises(WorkerError):
            PapiWorker(queue=QueueSpy(), registry=HandlerRegistry(),
                policy={"execution_enabled": False}, worker_id=" ")


    def test_worker_does_not_report_completion_after_lease_is_lost(self):
        class LeaseLostQueue(QueueSpy):
            def __init__(self, job):
                super().__init__(job)
                self.store = FakeStore()
                self.complete_calls = []

            def complete(self, **kwargs):
                self.complete_calls.append(kwargs)
                return False

        job = {"id": "job-lease", "task_id": "task-lease", "handler": "report.preview",
               "payload": {}, "lease_token": "lease-stale", "agent_identity": {"signed": True}}
        queue = LeaseLostQueue(job)
        registry = HandlerRegistry()
        registry.register("report.preview", "read_only", lambda payload, context: {"ok": True})
        policy = {"execution_enabled": True, "allowed_handlers": ["report.preview"],
                  "action_permissions": {"read_only": {"enabled": True, "owner_approval": False}},
                  "external_actions_enabled": False}
        with tempfile.TemporaryDirectory() as tmp:
            worker = PapiWorker(queue=queue, registry=registry, policy=policy,
                worker_id="worker-test", key_dir=Path(tmp) / "keys",
                replay_db=Path(tmp) / "replay.sqlite3")
            with patch("papi_core.worker.authorize_authenticated_agent",
                       return_value={"principal": "agent-a"}), \
                 patch("papi_core.worker.execute_authorized_job", return_value={"ok": True}):
                result = worker.run_once()

        self.assertEqual(result["status"], "lease_lost")
        self.assertEqual(len(queue.complete_calls), 1)
        self.assertEqual(queue.complete_calls[0]["lease_token"], "lease-stale")
        self.assertEqual(queue.fail_calls, [])

    def test_worker_blocks_job_without_signed_agent_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            job = {"id": "job-1", "task_id": "task-1", "handler": "report.preview",
                   "payload": {}, "lease_token": "lease-1", "agent_identity": None}
            queue = QueueSpy(job)
            queue.store = FakeStore()
            registry = HandlerRegistry()
            registry.register("report.preview", "read_only", lambda payload, context: {"ok": True})
            policy = {"execution_enabled": True, "allowed_handlers": ["report.preview"],
                      "action_permissions": {"read_only": {"enabled": True, "owner_approval": False}},
                      "external_actions_enabled": False}
            worker = PapiWorker(queue=queue, registry=registry, policy=policy,
                worker_id="worker-test", key_dir=Path(tmp) / "keys",
                replay_db=Path(tmp) / "replay.sqlite3")
            result = worker.run_once()
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(len(queue.fail_calls), 1)
            self.assertEqual(queue.fail_calls[0]["error_code"], "authentication_failed")


if __name__ == "__main__":
    unittest.main()
