import unittest
from datetime import datetime, timezone

from papi_core.lease_recovery import assess_lease_recovery
from papi_core.queue_observability import evaluate_queue_snapshot
from papi_core.retry_policy import decide_retry


NOW = datetime(2026, 11, 13, 15, 0, tzinfo=timezone.utc)


class RetryQueueFinalIntegrationTests(unittest.TestCase):
    def test_transient_failure_retry_and_lease_recovery_are_consistent(self):
        decision = decide_retry(
            error_code="service_timeout", attempt=2, max_attempts=5,
            base_delay_seconds=15, max_delay_seconds=3600,
            jitter_fraction=0, jitter_sample=0.5,
        )
        self.assertTrue(decision.retry)
        self.assertEqual(decision.delay_seconds, 30)

        recovered = assess_lease_recovery({
            "status": "running", "attempts": 2, "max_attempts": 5,
            "lease_until": "2026-11-13T14:59:00Z",
            "lease_token": "must-not-leak", "lease_owner": "worker-private",
        }, now=NOW)
        self.assertEqual(recovered["decision"], "reclaim")
        self.assertTrue(recovered["claim_eligible"])
        self.assertNotIn("must-not-leak", repr(recovered))
        self.assertNotIn("worker-private", repr(recovered))

        snapshot = evaluate_queue_snapshot([{
            "id": "private-job-id", "status": "retry",
            "attempts": 2, "max_attempts": 5,
            "created_at": "2026-11-13T14:55:00Z",
            "available_at": "2026-11-13T14:59:30Z",
            "payload": {"customer": "private"},
        }], now=NOW)
        self.assertEqual(snapshot["counts"]["retry"], 1)
        self.assertEqual(snapshot["due_retries"], 1)
        self.assertEqual(snapshot["active_backlog"], 1)
        self.assertNotIn("private-job-id", repr(snapshot))
        self.assertNotIn("customer", repr(snapshot))

    def test_permanent_error_does_not_schedule_retry(self):
        decision = decide_retry(
            error_code="permission_denied", attempt=1, max_attempts=5
        )
        self.assertFalse(decision.retry)
        self.assertEqual(decision.reason, "permanent_error")

    def test_stale_running_grace_period_is_enforced(self):
        job = {
            "id": "running-job", "status": "running",
            "attempts": 1, "max_attempts": 5,
            "lease_until": "2026-11-13T14:59:00Z",
        }
        within_grace = evaluate_queue_snapshot(
            [job], now=NOW, stale_running_seconds=120
        )
        self.assertEqual(within_grace["expired_running_leases"], 0)
        self.assertEqual(within_grace["overall_status"], "healthy")

        beyond_grace = evaluate_queue_snapshot(
            [job], now=NOW, stale_running_seconds=60
        )
        self.assertEqual(beyond_grace["expired_running_leases"], 1)
        self.assertEqual(beyond_grace["overall_status"], "degraded")


if __name__ == "__main__":
    unittest.main()
