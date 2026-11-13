"""Fenced lease-renewal queue tests."""
import unittest

from papi_core.execution_queue import ExecutionQueue, QueueError


class FakeStore:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def _request(self, method, path, payload=None, prefer=None):
        self.calls.append((method, path, payload))
        return self.response


class ExecutionQueueRenewTests(unittest.TestCase):
    def test_renew_uses_current_worker_and_lease_fence(self):
        store = FakeStore(True)
        queue = ExecutionQueue(store)
        self.assertTrue(queue.renew(
            job_id="job-1", worker_id="worker-1",
            lease_token="00000000-0000-4000-8000-000000000001",
            lease_seconds=300,
        ))
        method, path, payload = store.calls[0]
        self.assertEqual((method, path), ("POST", "rpc/papi_renew_job"))
        self.assertEqual(payload["p_job_id"], "job-1")
        self.assertEqual(payload["p_worker_id"], "worker-1")
        self.assertEqual(payload["p_lease_seconds"], 300)

    def test_renew_returns_false_when_fence_is_lost_or_expired(self):
        store = FakeStore(False)
        queue = ExecutionQueue(store)
        self.assertFalse(queue.renew(
            job_id="job-1", worker_id="worker-1",
            lease_token="00000000-0000-4000-8000-000000000001",
        ))

    def test_renew_rejects_invalid_duration_before_rpc(self):
        store = FakeStore(True)
        queue = ExecutionQueue(store)
        with self.assertRaises(QueueError):
            queue.renew(
                job_id="job-1", worker_id="worker-1",
                lease_token="00000000-0000-4000-8000-000000000001",
                lease_seconds=10,
            )
        self.assertEqual(store.calls, [])


if __name__ == "__main__":
    unittest.main()
