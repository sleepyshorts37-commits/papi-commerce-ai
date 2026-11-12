import unittest
from runtime.papi_core.opportunity_monitor import monitor_opportunities


def item(oid="A", score=80, status="active", observed_at="2026-11-10", **extra):
    return {"opportunity_id": oid, "title": "Freelance service", "observed_at": observed_at,
            "score": score, "decision": "test", "status": status, **extra}


class MonitorTests(unittest.TestCase):
    def test_new_and_improved(self):
        r = monitor_opportunities([item(score=60)], [item(score=80), item("B")], as_of="2026-11-12")
        self.assertEqual(r["summary"]["improved"], 1)
        self.assertEqual(r["summary"]["new"], 1)

    def test_stale(self):
        r = monitor_opportunities([], [item(observed_at="2026-10-01")], as_of="2026-11-12")
        self.assertEqual(r["summary"]["stale"], 1)

    def test_missing_is_not_closed(self):
        r = monitor_opportunities([item()], [], as_of="2026-11-12")
        self.assertEqual(r["disappeared_opportunities"][0]["meaning"],
                         "absent_from_current_snapshot_not_proof_of_closure")

    def test_verified_payment(self):
        r = monitor_opportunities([], [item(verified_payment_xof=25000, payment_reference="PAY-1",
                                            payment_verified_by="operator")], as_of="2026-11-12")
        self.assertEqual(r["summary"]["verified_revenue_xof"], 25000)

    def test_payment_requires_reference(self):
        with self.assertRaises(ValueError):
            monitor_opportunities([], [item(verified_payment_xof=25000)], as_of="2026-11-12")

    def test_duplicate_ids(self):
        with self.assertRaises(ValueError):
            monitor_opportunities([], [item(), item()], as_of="2026-11-12")

    def test_future_date(self):
        with self.assertRaises(ValueError):
            monitor_opportunities([], [item(observed_at="2026-11-13")], as_of="2026-11-12")


if __name__ == "__main__":
    unittest.main()
