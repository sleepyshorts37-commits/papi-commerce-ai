import unittest

from runtime.papi_core.order_manager import analyze_orders


NOW = "2026-11-12T12:00:00+00:00"


def order(order_id="O-1", status="draft", history=None, updated=None, **extra):
    history = history or [{"status": "draft", "at": NOW}]
    return {
        "order_id": order_id,
        "client_ref": "CLIENT-ANON-1",
        "business_unit": "PAPI_MARKET",
        "order_summary": "Commande de fournitures",
        "status": status,
        "created_at": history[0]["at"],
        "updated_at": updated or history[-1]["at"],
        "status_history": history,
        **extra,
    }


class OrderManagerTests(unittest.TestCase):
    def test_valid_draft_order(self):
        result = analyze_orders([order()], as_of=NOW)
        self.assertEqual(result["counts"]["valid"], 1)
        self.assertEqual(result["counts"]["by_status"]["draft"], 1)

    def test_valid_lifecycle_and_terminal_status(self):
        history = [
            {"status": "draft", "at": NOW},
            {"status": "confirmed", "at": "2026-11-12T12:05:00+00:00"},
            {"status": "preparing", "at": "2026-11-12T12:10:00+00:00"},
            {"status": "ready", "at": "2026-11-12T12:20:00+00:00"},
            {"status": "dispatched", "at": "2026-11-12T12:30:00+00:00"},
            {"status": "delivered", "at": "2026-11-12T13:00:00+00:00"},
        ]
        result = analyze_orders([order(status="delivered", history=history)], as_of="2026-11-12T14:00:00+00:00")
        self.assertEqual(result["counts"]["by_status"]["delivered"], 1)
        self.assertEqual(result["queues"]["active_order_ids"], [])

    def test_rejects_skipped_transition(self):
        history = [
            {"status": "draft", "at": NOW},
            {"status": "dispatched", "at": "2026-11-12T12:10:00+00:00"},
        ]
        result = analyze_orders([order(status="dispatched", history=history)], as_of="2026-11-12T13:00:00+00:00")
        self.assertEqual(result["counts"]["rejected"], 1)

    def test_rejects_duplicate_order_id(self):
        result = analyze_orders([order(), order()], as_of=NOW)
        self.assertEqual(result["counts"]["valid"], 1)
        self.assertEqual(result["counts"]["rejected"], 1)

    def test_rejects_personal_contact_fields(self):
        result = analyze_orders([order(phone="+221770000000")], as_of=NOW)
        self.assertEqual(result["counts"]["rejected"], 1)

    def test_rejects_mismatched_current_status(self):
        result = analyze_orders([order(status="confirmed")], as_of=NOW)
        self.assertEqual(result["counts"]["rejected"], 1)

    def test_flags_dispatches_older_than_48_hours(self):
        history = [
            {"status": "draft", "at": "2026-11-09T12:00:00+00:00"},
            {"status": "confirmed", "at": "2026-11-09T12:10:00+00:00"},
            {"status": "preparing", "at": "2026-11-09T12:20:00+00:00"},
            {"status": "ready", "at": "2026-11-09T12:30:00+00:00"},
            {"status": "dispatched", "at": "2026-11-09T13:00:00+00:00"},
        ]
        result = analyze_orders(
            [order(status="dispatched", history=history)],
            as_of="2026-11-12T12:00:00+00:00",
        )
        self.assertEqual(result["queues"]["dispatched_48h_or_more"], ["O-1"])

    def test_cancelled_order_is_not_active(self):
        history = [
            {"status": "draft", "at": NOW},
            {"status": "cancelled", "at": "2026-11-12T12:05:00+00:00"},
        ]
        result = analyze_orders(
            [order(status="cancelled", history=history)],
            as_of="2026-11-12T13:00:00+00:00",
        )
        self.assertEqual(result["queues"]["active_order_ids"], [])


if __name__ == "__main__":
    unittest.main()
