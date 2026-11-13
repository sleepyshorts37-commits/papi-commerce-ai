import unittest
from datetime import datetime, timezone, timedelta

from papi_core.monitoring import MonitoringError, evaluate_health_snapshot


class MonitoringTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)

    def signal(self, name="api", status="healthy", observed=None):
        return {"id": name, "status": status,
                "observed_at": (observed or self.now).isoformat(),
                "detail": "must not be copied to output"}

    def test_healthy_snapshot(self):
        result = evaluate_health_snapshot([self.signal()], now=self.now)
        self.assertEqual(result["overall_status"], "healthy")
        self.assertEqual(result["counts"]["healthy"], 1)
        self.assertFalse(result["network_probes_performed"])

    def test_unavailable_signal_creates_incident(self):
        result = evaluate_health_snapshot([self.signal(status="unavailable")], now=self.now)
        self.assertEqual(result["overall_status"], "unavailable")
        self.assertEqual(result["incidents"][0]["check_id"], "api")
        self.assertNotIn("detail", result["checks"][0])
        self.assertNotIn("detail", result["incidents"][0])
        self.assertNotIn("must not be copied to output", repr(result))

    def test_stale_signal_becomes_unknown(self):
        old = self.now - timedelta(seconds=301)
        result = evaluate_health_snapshot([self.signal(observed=old)], now=self.now)
        self.assertEqual(result["checks"][0]["status"], "unknown")
        self.assertEqual(result["checks"][0]["reason"], "stale_signal")

    def test_future_signal_becomes_unknown(self):
        future = self.now + timedelta(minutes=2)
        result = evaluate_health_snapshot([self.signal(observed=future)], now=self.now)
        self.assertEqual(result["checks"][0]["reason"], "timestamp_in_future")

    def test_most_severe_state_wins(self):
        checks = [self.signal("one", "degraded"), self.signal("two", "unavailable")]
        self.assertEqual(evaluate_health_snapshot(checks, now=self.now)["overall_status"], "unavailable")

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(MonitoringError):
            evaluate_health_snapshot([self.signal(), self.signal()], now=self.now)

    def test_naive_now_rejected(self):
        with self.assertRaises(MonitoringError):
            evaluate_health_snapshot([], now=datetime(2026, 11, 13, 12, 0))

    def test_naive_observation_rejected(self):
        with self.assertRaises(MonitoringError):
            evaluate_health_snapshot([self.signal(observed=datetime(2026, 11, 13, 12, 0))], now=self.now)

    def test_invalid_staleness_threshold_rejected(self):
        with self.assertRaises(MonitoringError):
            evaluate_health_snapshot([], now=self.now, stale_after_seconds=0)


if __name__ == "__main__":
    unittest.main()
