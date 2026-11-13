import unittest
from datetime import datetime, timezone

from papi_core.lease_recovery import LeaseRecoveryError, assess_lease_recovery


NOW = datetime(2026, 11, 13, 15, 0, tzinfo=timezone.utc)


def running(**changes):
    job = {
        "status": "running", "attempts": 2, "max_attempts": 5,
        "lease_until": "2026-11-13T14:59:59Z",
        "lease_token": "secret-token", "lease_owner": "private-worker",
    }
    job.update(changes)
    return job


class LeaseRecoveryTests(unittest.TestCase):
    def test_expired_lease_with_attempts_remaining_is_reclaimable(self):
        result = assess_lease_recovery(running(), now=NOW)
        self.assertEqual(result["decision"], "reclaim")
        self.assertTrue(result["claim_eligible"])
        self.assertFalse(result["terminal"])

    def test_unexpired_lease_must_not_be_stolen(self):
        result = assess_lease_recovery(
            running(lease_until="2026-11-13T15:00:01Z"), now=NOW
        )
        self.assertEqual(result["decision"], "wait_for_lease_expiry")
        self.assertFalse(result["claim_eligible"])

    def test_expired_lease_at_attempt_ceiling_is_terminal(self):
        result = assess_lease_recovery(
            running(attempts=5, max_attempts=5), now=NOW
        )
        self.assertEqual(result["decision"], "terminalize")
        self.assertTrue(result["terminal"])
        self.assertFalse(result["claim_eligible"])

    def test_queued_job_with_attempts_remaining_is_claim_eligible(self):
        result = assess_lease_recovery(
            running(status="queued", attempts=0), now=NOW
        )
        self.assertEqual(result["decision"], "not_running")
        self.assertTrue(result["claim_eligible"])

    def test_queued_job_at_attempt_ceiling_is_not_claim_eligible(self):
        result = assess_lease_recovery(
            running(status="queued", attempts=5, max_attempts=5), now=NOW
        )
        self.assertFalse(result["claim_eligible"])

    def test_terminal_job_is_not_claim_eligible(self):
        result = assess_lease_recovery(running(status="failed"), now=NOW)
        self.assertTrue(result["terminal"])
        self.assertFalse(result["claim_eligible"])

    def test_lease_at_exact_expiry_is_expired(self):
        result = assess_lease_recovery(
            running(lease_until="2026-11-13T15:00:00Z"), now=NOW
        )
        self.assertEqual(result["decision"], "reclaim")

    def test_lease_token_and_owner_are_not_emitted(self):
        result = assess_lease_recovery(running(), now=NOW)
        self.assertNotIn("secret-token", repr(result))
        self.assertNotIn("private-worker", repr(result))
        self.assertFalse(result["lease_token_exposed"])

    def test_naive_timestamp_is_rejected(self):
        with self.assertRaises(LeaseRecoveryError):
            assess_lease_recovery(
                running(lease_until="2026-11-13T14:59:59"), now=NOW
            )

    def test_invalid_attempt_metadata_is_rejected(self):
        with self.assertRaises(LeaseRecoveryError):
            assess_lease_recovery(running(attempts=True), now=NOW)

    def test_naive_now_is_rejected(self):
        with self.assertRaises(LeaseRecoveryError):
            assess_lease_recovery(running(), now=datetime(2026, 11, 13, 15))


if __name__ == "__main__":
    unittest.main()
