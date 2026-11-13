"""Tests for durable identifiers returned by atomic job reservations."""
import unittest

from papi_core.execution_queue import ExecutionQueue, QueueError


VALID_ATTEMPT = "00000000-0000-4000-8000-000000000001"


class FakeStore:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def _request(self, method, path, payload=None, prefer=None):
        self.calls.append((method, path, payload))
        return self.response


class ExecutionQueueAttemptIdTests(unittest.TestCase):
    def test_claim_returns_canonical_attempt_id(self):
        store = FakeStore({
            "id": "job-1", "lease_token": "lease-1",
            "attempt_id": VALID_ATTEMPT.upper(),
        })
        claimed = ExecutionQueue(store).claim(worker_id="worker-1")
        self.assertEqual(claimed["attempt_id"], VALID_ATTEMPT)
        self.assertEqual(claimed["id"], "job-1")

    def test_claim_rejects_missing_attempt_id(self):
        store = FakeStore({"id": "job-1", "lease_token": "lease-1"})
        with self.assertRaises(QueueError):
            ExecutionQueue(store).claim(worker_id="worker-1")

    def test_claim_rejects_malformed_attempt_id(self):
        store = FakeStore({
            "id": "job-1", "lease_token": "lease-1", "attempt_id": "not-a-uuid",
        })
        with self.assertRaises(QueueError):
            ExecutionQueue(store).claim(worker_id="worker-1")


if __name__ == "__main__":
    unittest.main()
