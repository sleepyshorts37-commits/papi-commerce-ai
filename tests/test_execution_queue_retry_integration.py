"""Tests for the retry decision passed from Python to the durable queue RPC."""
import unittest

from papi_core.execution_queue import ExecutionQueue, QueueError


class RecordingStore:
    def __init__(self, response="retry"):
        self.response = response
        self.calls = []

    def _request(self, method, path, payload=None, prefer=None):
        self.calls.append((method, path, payload, prefer))
        return self.response


class ExecutionQueueRetryIntegrationTests(unittest.TestCase):
    def make_queue(self, response="retry"):
        store = RecordingStore(response)
        return ExecutionQueue(store), store

    def test_transient_error_sends_bounded_delay_and_retry_flag(self):
        queue, store = self.make_queue("retry")
        result = queue.fail(
            job_id="job-1", worker_id="worker-1", lease_token="lease-1",
            error_code="service_timeout", attempt=2, max_attempts=5,
            jitter_sample=0.5,
        )
        self.assertEqual(result, "retry")
        payload = store.calls[0][2]
        self.assertEqual(payload["p_retry_allowed"], True)
        self.assertEqual(payload["p_retry_delay_seconds"], 30)
        self.assertEqual(payload["p_error_code"], "service_timeout")

    def test_permanent_error_never_requests_retry(self):
        queue, store = self.make_queue("failed")
        queue.fail(
            job_id="job-2", worker_id="worker-1", lease_token="lease-2",
            error_code="permission_denied", attempt=1, max_attempts=5,
        )
        payload = store.calls[0][2]
        self.assertFalse(payload["p_retry_allowed"])
        self.assertEqual(payload["p_retry_delay_seconds"], 0)

    def test_attempt_ceiling_never_requests_retry(self):
        queue, store = self.make_queue("failed")
        queue.fail(
            job_id="job-3", worker_id="worker-1", lease_token="lease-3",
            error_code="service_timeout", attempt=5, max_attempts=5,
        )
        payload = store.calls[0][2]
        self.assertFalse(payload["p_retry_allowed"])
        self.assertEqual(payload["p_retry_delay_seconds"], 0)

    def test_delay_is_capped_at_one_hour(self):
        queue, store = self.make_queue("retry")
        queue.fail(
            job_id="job-4", worker_id="worker-1", lease_token="lease-4",
            error_code="rate_limited", attempt=20, max_attempts=25,
        )
        self.assertEqual(store.calls[0][2]["p_retry_delay_seconds"], 3600)

    def test_invalid_attempt_does_not_call_rpc(self):
        queue, store = self.make_queue("failed")
        with self.assertRaises(QueueError):
            queue.fail(
                job_id="job-5", worker_id="worker-1", lease_token="lease-5",
                error_code="service_timeout", attempt=0, max_attempts=5,
            )
        self.assertEqual(store.calls, [])

    def test_retryable_code_is_required_even_if_attempts_remain(self):
        queue, store = self.make_queue("failed")
        queue.fail(
            job_id="job-6", worker_id="worker-1", lease_token="lease-6",
            error_code="unknown_error", attempt=1, max_attempts=5,
        )
        self.assertFalse(store.calls[0][2]["p_retry_allowed"])


if __name__ == "__main__":
    unittest.main()
