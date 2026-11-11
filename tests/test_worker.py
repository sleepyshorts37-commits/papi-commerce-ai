import unittest

from papi_core.handler_registry import HandlerRegistry
from papi_core.worker import PapiWorker, WorkerError


class QueueSpy:
    def __init__(self, claim_result=None):
        self.claim_result = claim_result
        self.claim_calls = 0

    def claim(self, *, worker_id):
        self.claim_calls += 1
        return self.claim_result


class WorkerSafetyTests(unittest.TestCase):
    def test_disabled_worker_does_not_claim_a_job(self):
        queue = QueueSpy()
        worker = PapiWorker(
            queue=queue,
            registry=HandlerRegistry(),
            policy={"execution_enabled": False},
            worker_id="worker-test",
        )

        result = worker.run_once()

        self.assertEqual(result, {"status": "disabled", "claimed": False})
        self.assertEqual(queue.claim_calls, 0)

    def test_enabled_worker_with_empty_queue_returns_idle(self):
        queue = QueueSpy()
        worker = PapiWorker(
            queue=queue,
            registry=HandlerRegistry(),
            policy={"execution_enabled": True},
            worker_id="worker-test",
        )

        result = worker.run_once()

        self.assertEqual(result, {"status": "idle", "claimed": False})
        self.assertEqual(queue.claim_calls, 1)

    def test_blank_worker_id_is_rejected(self):
        with self.assertRaises(WorkerError):
            PapiWorker(
                queue=QueueSpy(),
                registry=HandlerRegistry(),
                policy={"execution_enabled": False},
                worker_id=" ",
            )


if __name__ == "__main__":
    unittest.main()
