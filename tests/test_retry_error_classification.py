"""Tests for safe transient transport classification and claim metadata."""
import unittest
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from papi_core.execution_queue import ExecutionQueue, QueueError
from papi_core.storage import StoreError, SupabaseStore


class RecordingStore:
    def __init__(self, response):
        self.response = response

    def _request(self, method, path, payload=None, prefer=None):
        return self.response


class RetryClassificationTests(unittest.TestCase):
    def make_store(self):
        return SupabaseStore(url="https://example.supabase.co", key="test-key")

    def test_http_429_is_rate_limited(self):
        error = HTTPError("https://example.invalid", 429, "limited", {}, None)
        with patch("papi_core.storage.urlopen", side_effect=error):
            with self.assertRaises(StoreError) as caught:
                self.make_store()._request("GET", "papi_jobs")
        self.assertEqual(caught.exception.retry_code, "rate_limited")

    def test_http_gateway_errors_are_transient(self):
        for code, expected in ((408, "service_timeout"), (425, "temporarily_unavailable"),
                               (500, "temporarily_unavailable"), (502, "temporarily_unavailable"),
                               (503, "temporarily_unavailable"), (504, "service_timeout")):
            error = HTTPError("https://example.invalid", code, "failure", {}, None)
            with self.subTest(code=code), patch("papi_core.storage.urlopen", side_effect=error):
                with self.assertRaises(StoreError) as caught:
                    self.make_store()._request("GET", "papi_jobs")
                self.assertEqual(caught.exception.retry_code, expected)

    def test_http_auth_and_validation_errors_are_not_retryable(self):
        for code in (400, 401, 403, 404, 409):
            error = HTTPError("https://example.invalid", code, "failure", {}, None)
            with self.subTest(code=code), patch("papi_core.storage.urlopen", side_effect=error):
                with self.assertRaises(StoreError) as caught:
                    self.make_store()._request("GET", "papi_jobs")
                self.assertIsNone(caught.exception.retry_code)

    def test_timeout_and_connection_reset_are_classified_without_message_parsing(self):
        with patch("papi_core.storage.urlopen", side_effect=URLError(TimeoutError())):
            with self.assertRaises(StoreError) as caught:
                self.make_store()._request("GET", "papi_jobs")
        self.assertEqual(caught.exception.retry_code, "service_timeout")

        with patch("papi_core.storage.urlopen", side_effect=URLError(ConnectionResetError())):
            with self.assertRaises(StoreError) as caught:
                self.make_store()._request("GET", "papi_jobs")
        self.assertEqual(caught.exception.retry_code, "connection_reset")

    def test_claim_requires_attempt_ceiling_from_database(self):
        queue = ExecutionQueue(RecordingStore({
            "id": "job-1", "lease_token": "lease-1", "attempts": 2
        }))
        with self.assertRaises(QueueError):
            queue.claim(worker_id="worker-1")

    def test_claim_accepts_durable_attempt_metadata(self):
        queue = ExecutionQueue(RecordingStore({
            "id": "job-1", "lease_token": "lease-1",
            "attempts": 2, "max_attempts": 7,
        }))
        claimed = queue.claim(worker_id="worker-1")
        self.assertEqual(claimed["max_attempts"], 7)
        self.assertEqual(claimed["attempts"], 2)

    def test_claim_rejects_inconsistent_attempt_metadata(self):
        for attempts, ceiling in ((0, 5), (6, 5), (1, 11), (True, 5), (1, True)):
            with self.subTest(attempts=attempts, ceiling=ceiling):
                queue = ExecutionQueue(RecordingStore({
                    "id": "job-1", "lease_token": "lease-1",
                    "attempts": attempts, "max_attempts": ceiling,
                }))
                with self.assertRaises(QueueError):
                    queue.claim(worker_id="worker-1")


if __name__ == "__main__":
    unittest.main()
