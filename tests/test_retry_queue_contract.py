"""Contrats d'intégration offline entre décision retry et limites de file."""
import unittest

from papi_core.retry_policy import decide_retry


class RetryQueueContractTests(unittest.TestCase):
    def test_transient_failure_retries_only_below_attempt_ceiling(self):
        for attempt in range(1, 5):
            with self.subTest(attempt=attempt):
                decision = decide_retry(error_code="service_timeout", attempt=attempt,
                                        max_attempts=5, jitter_fraction=0)
                self.assertTrue(decision.retry)
                self.assertGreaterEqual(decision.delay_seconds, 0)
        terminal = decide_retry(error_code="service_timeout", attempt=5,
                                max_attempts=5, jitter_fraction=0)
        self.assertFalse(terminal.retry)
        self.assertEqual(terminal.reason, "attempt_limit_reached")

    def test_permanent_failure_never_enters_retry_path(self):
        for code in ("permission_denied", "invalid_payload", "unknown_error"):
            with self.subTest(code=code):
                decision = decide_retry(error_code=code, attempt=1, max_attempts=5)
                self.assertFalse(decision.retry)
                self.assertEqual(decision.delay_seconds, 0)

    def test_delay_is_monotonic_and_bounded_without_jitter(self):
        delays = [decide_retry(error_code="connection_reset", attempt=n,
                               max_attempts=10, base_delay_seconds=2,
                               max_delay_seconds=20, jitter_fraction=0).delay_seconds
                  for n in range(1, 10)]
        self.assertEqual(delays, sorted(delays))
        self.assertLessEqual(max(delays), 20)

    def test_jitter_extremes_remain_within_cap(self):
        for sample in (0, 0.5, 1):
            with self.subTest(sample=sample):
                decision = decide_retry(error_code="rate_limited", attempt=4,
                                        max_attempts=8, max_delay_seconds=30,
                                        jitter_fraction=1, jitter_sample=sample)
                self.assertGreaterEqual(decision.delay_seconds, 0)
                self.assertLessEqual(decision.delay_seconds, 30)


if __name__ == "__main__":
    unittest.main()
