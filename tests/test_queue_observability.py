import unittest
from datetime import datetime, timezone

from papi_core.queue_observability import (
    QueueObservabilityError,
    evaluate_queue_snapshot,
)


NOW = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)


def job(job_id="j1", status="queued", **overrides):
    value = {
        "id": job_id, "status": status, "attempts": 0, "max_attempts": 5,
        "created_at": "2026-11-13T11:55:00Z",
        "available_at": "2026-11-13T12:00:00Z",
        "lease_until": "2026-11-13T12:05:00Z",
        "payload": {"private": "must-not-leak"},
    }
    value.update(overrides)
    return value


class QueueObservabilityTests(unittest.TestCase):
    def test_empty_snapshot_is_healthy_with_zero_counts(self):
        result = evaluate_queue_snapshot([], now=NOW)
        self.assertEqual(result["overall_status"], "healthy")
        self.assertEqual(result["total_jobs"], 0)
        self.assertIsNone(result["oldest_queued_or_retry_age_seconds"])

    def test_counts_backlog_and_oldest_age_are_derived(self):
        result = evaluate_queue_snapshot([
            job("a"), job("b", "retry", attempts=2,
                          available_at="2026-11-13T12:00:30Z"),
            job("c", "done"),
        ], now=NOW)
        self.assertEqual(result["counts"]["queued"], 1)
        self.assertEqual(result["counts"]["retry"], 1)
        self.assertEqual(result["active_backlog"], 2)
        self.assertEqual(result["oldest_queued_or_retry_age_seconds"], 300)
        self.assertEqual(result["due_retries"], 0)
        self.assertEqual(result["next_retry_in_seconds"], 30)

    def test_due_retry_is_counted(self):
        result = evaluate_queue_snapshot([
            job(status="retry", available_at="2026-11-13T11:59:00Z")
        ], now=NOW)
        self.assertEqual(result["due_retries"], 1)

    def test_expired_lease_degrades_health(self):
        result = evaluate_queue_snapshot([
            job(status="running", lease_until="2026-11-13T11:59:59Z")
        ], now=NOW)
        self.assertEqual(result["overall_status"], "degraded")
        self.assertEqual(result["expired_running_leases"], 1)
        self.assertIn("expired_running_lease", result["alert_reasons"])

    def test_active_job_at_attempt_ceiling_degrades_health(self):
        result = evaluate_queue_snapshot([
            job(status="retry", attempts=5, max_attempts=5)
        ], now=NOW)
        self.assertEqual(result["active_jobs_at_attempt_ceiling"], 1)
        self.assertIn("active_job_at_attempt_ceiling", result["alert_reasons"])

    def test_terminal_job_at_attempt_ceiling_is_not_active_alert(self):
        result = evaluate_queue_snapshot([
            job(status="failed", attempts=5, max_attempts=5)
        ], now=NOW)
        self.assertEqual(result["active_jobs_at_attempt_ceiling"], 0)
        self.assertEqual(result["overall_status"], "healthy")

    def test_payload_and_identifiers_are_not_emitted(self):
        result = evaluate_queue_snapshot([job("sensitive-id")], now=NOW)
        self.assertNotIn("sensitive-id", repr(result))
        self.assertNotIn("private", repr(result))
        self.assertFalse(result["database_or_network_access_performed"])

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(QueueObservabilityError):
            evaluate_queue_snapshot([job("x"), job("x")], now=NOW)

    def test_unknown_status_rejected(self):
        with self.assertRaises(QueueObservabilityError):
            evaluate_queue_snapshot([job(status="pending")], now=NOW)

    def test_invalid_attempt_metadata_rejected(self):
        with self.assertRaises(QueueObservabilityError):
            evaluate_queue_snapshot([job(attempts=True)], now=NOW)

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(QueueObservabilityError):
            evaluate_queue_snapshot([job(created_at="2026-11-13T11:55:00")], now=NOW)

    def test_invalid_clock_and_threshold_rejected(self):
        with self.assertRaises(QueueObservabilityError):
            evaluate_queue_snapshot([], now=datetime(2026, 11, 13))
        with self.assertRaises(QueueObservabilityError):
            evaluate_queue_snapshot([], now=NOW, stale_running_seconds=True)


if __name__ == "__main__":
    unittest.main()
