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



class ExecutionQueueFailurePolicyTests(unittest.TestCase):
    def test_fail_sends_explicit_retryability_to_rpc(self):
        store = FakeStore("retry")
        result = ExecutionQueue(store).fail(
            job_id="job-1", worker_id="worker-1", lease_token="lease-1",
            error_code="storage_unavailable", retryable=True,
        )
        self.assertEqual(result, "retry")
        method, path, payload = store.calls[0]
        self.assertEqual((method, path), ("POST", "rpc/papi_fail_job"))
        self.assertIs(payload["p_retryable"], True)

    def test_terminal_failure_is_not_retried(self):
        store = FakeStore("failed")
        result = ExecutionQueue(store).fail(
            job_id="job-1", worker_id="worker-1", lease_token="lease-1",
            error_code="permission_denied", retryable=False,
        )
        self.assertEqual(result, "failed")
        self.assertIs(store.calls[0][2]["p_retryable"], False)

    def test_fail_rejects_non_boolean_retryability(self):
        store = FakeStore("retry")
        with self.assertRaises(QueueError):
            ExecutionQueue(store).fail(
                job_id="job-1", worker_id="worker-1", lease_token="lease-1",
                error_code="storage_unavailable", retryable=1,
            )
        self.assertEqual(store.calls, [])


if __name__ == "__main__":
    unittest.main()
