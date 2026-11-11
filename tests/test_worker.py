import unittest
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
