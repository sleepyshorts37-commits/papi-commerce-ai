import unittest
from unittest.mock import patch

from papi_core.job_queue import SupabaseJobQueue
from papi_core.storage import StoreError, SupabaseStore


class SupabaseJobQueueTests(unittest.TestCase):
    def setUp(self):
        self.store = SupabaseStore(url="https://example.supabase.co", key="test-key")
        self.queue = SupabaseJobQueue(self.store)
        self.token = "123e4567-e89b-12d3-a456-426614174000"

    def test_enqueue_uses_unique_idempotency_key(self):
        row = {"id": "JOB-1"}
        with patch.object(self.store, "_request", return_value=[row]) as request:
            self.assertEqual(self.queue.enqueue(
                job_id="JOB-1", task_id="TASK-1", handler="pdf.generate",
                payload={"format": "pdf"}, idempotency_key="TASK-1:pdf:v1",
            ), row)
        self.assertEqual(request.call_args.args[1], "papi_jobs")
        self.assertEqual(request.call_args.args[2]["idempotency_key"], "TASK-1:pdf:v1")

    def test_enqueue_rejects_invalid_handler_and_payload(self):
        with patch.object(self.store, "_request") as request:
            with self.assertRaises(StoreError):
                self.queue.enqueue(job_id="J", task_id="T", handler="../shell",
                    payload={}, idempotency_key="K")
            with self.assertRaises(StoreError):
                self.queue.enqueue(job_id="J", task_id="T", handler="worker.run",
                    payload=[], idempotency_key="K")
        request.assert_not_called()

    def test_claim_returns_none_when_queue_empty(self):
        with patch.object(self.store, "_request", return_value=None) as request:
            self.assertIsNone(self.queue.claim(worker_id="agent-a", lease_token=self.token))
        self.assertEqual(request.call_args.args[1], "rpc/papi_claim_job")

    def test_claim_validates_response_and_token(self):
        payload = {"id": "J", "task_id": "T", "handler": "pdf.generate",
            "payload": {}, "attempts": 1, "lease_token": self.token,
            "lease_until": "2026-11-12T10:02:00Z"}
        with patch.object(self.store, "_request", return_value=payload):
            self.assertEqual(self.queue.claim(worker_id="agent-a", lease_token=self.token), payload)
        payload["lease_token"] = "wrong"
        with patch.object(self.store, "_request", return_value=payload):
            with self.assertRaises(StoreError):
                self.queue.claim(worker_id="agent-a", lease_token=self.token)

    def test_heartbeat_and_complete_require_boolean_rpc_results(self):
        with patch.object(self.store, "_request", side_effect=[True, True]) as request:
            self.assertTrue(self.queue.heartbeat(job_id="J", worker_id="A", lease_token=self.token))
            self.assertTrue(self.queue.complete(job_id="J", worker_id="A", lease_token=self.token))
        self.assertEqual(request.call_count, 2)

    def test_fail_accepts_only_known_statuses(self):
        with patch.object(self.store, "_request", return_value="retry"):
            self.assertEqual(self.queue.fail(job_id="J", worker_id="A",
                lease_token=self.token, error_code="temporary_error"), "retry")
        with patch.object(self.store, "_request", return_value="done"):
            with self.assertRaises(StoreError):
                self.queue.fail(job_id="J", worker_id="A",
                    lease_token=self.token, error_code="temporary_error")

    def test_rejects_bad_lease_bounds_and_uuid(self):
        with patch.object(self.store, "_request") as request:
            with self.assertRaises(StoreError):
                self.queue.claim(worker_id="A", lease_token="not-a-uuid")
            with self.assertRaises(StoreError):
                self.queue.claim(worker_id="A", lease_token=self.token, lease_seconds=5)
        request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
