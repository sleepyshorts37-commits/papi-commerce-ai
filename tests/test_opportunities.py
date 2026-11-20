import unittest

from papi_core.opportunities import ACTIVITIES, OpportunityError, evaluate_opportunity, rank_opportunities


def opportunity(identifier="free-fast", **changes):
    item = {
        "id": identifier, "name": "Option de test", "activity": "PAPI SERVICES",
        "price_xof": 20000, "direct_cost_xof": 2000, "delivery_cost_xof": 0,
        "commission_pct": 0, "payment_fee_xof": 0, "refund_reserve_pct": 0,
        "initial_cost_xof": 0, "customer_advance_xof": 0,
        "supplier_payment_days": 0, "customer_payment_days": 0,
        "first_revenue_days": 3, "risk_pct": 10, "confidence_pct": 90,
    }
    item.update(changes)
    return item


class OpportunityTests(unittest.TestCase):
    def test_all_six_papi_activities_are_supported(self):
        for index, activity in enumerate(sorted(ACTIVITIES)):
            with self.subTest(activity=activity):
                result = evaluate_opportunity(opportunity(f"activity-{index}", activity=activity))
                self.assertEqual(result["activity"], activity)

    def test_commission_delivery_fees_and_reserve_reduce_contribution(self):
        result = evaluate_opportunity(opportunity(
            delivery_cost_xof=1500, commission_pct=10,
            payment_fee_xof=500, refund_reserve_pct=5,
        ))
        self.assertEqual(result["commission_xof"], 2000)
        self.assertEqual(result["refund_reserve_xof"], 1000)
        self.assertEqual(result["contribution_xof"], 13000)

    def test_supplier_due_before_customer_cash_creates_working_capital_need(self):
        result = evaluate_opportunity(opportunity(
            direct_cost_xof=7000, delivery_cost_xof=1000, payment_fee_xof=500,
            customer_advance_xof=2000, supplier_payment_days=0,
            customer_payment_days=7, initial_cost_xof=1500,
        ))
        self.assertEqual(result["cash_required_xof"], 8000)
        self.assertEqual(result["cash_in_days"], 10)

    def test_supplier_due_after_customer_cash_does_not_create_pre_receipt_gap(self):
        result = evaluate_opportunity(opportunity(
            direct_cost_xof=7000, delivery_cost_xof=1000,
            supplier_payment_days=14, customer_payment_days=7,
        ))
        self.assertEqual(result["cash_required_xof"], 0)

    def test_customer_advance_cannot_exceed_price(self):
        with self.assertRaises(OpportunityError):
            evaluate_opportunity(opportunity(customer_advance_xof=20001))

    def test_free_low_risk_fast_option_ranks_before_paid_option(self):
        paid = opportunity("paid", initial_cost_xof=4000, direct_cost_xof=1000, risk_pct=5, first_revenue_days=1)
        free = opportunity("free", risk_pct=15, first_revenue_days=5)
        ranked = rank_opportunities([paid, free])
        self.assertEqual([item["id"] for item in ranked], ["free", "paid"])
        self.assertEqual(ranked[0]["priority_tier"], 0)
        self.assertFalse(ranked[0]["external_action_enabled"])

    def test_unprofitable_options_are_ranked_last(self):
        good = opportunity("good")
        bad = opportunity("bad", direct_cost_xof=25000)
        ranked = rank_opportunities([bad, good])
        self.assertEqual(ranked[-1]["id"], "bad")
        self.assertEqual(ranked[-1]["recommendation"], "reject_or_rework")

    def test_expected_profit_accounts_for_confidence_and_startup_cost(self):
        result = evaluate_opportunity(opportunity(
            price_xof=10000, direct_cost_xof=2000,
            confidence_pct=50, initial_cost_xof=2500,
        ))
        self.assertEqual(result["expected_contribution_xof"], 4000)
        self.assertEqual(result["expected_net_after_setup_xof"], 1500)
        self.assertEqual(result["break_even_units"], 1)
        self.assertEqual(result["roi_pct"], 60.0)

    def test_boolean_money_and_non_finite_percentages_are_rejected(self):
        with self.assertRaises(OpportunityError):
            evaluate_opportunity(opportunity(price_xof=True))
        with self.assertRaises(OpportunityError):
            evaluate_opportunity(opportunity(risk_pct=float("nan")))
        with self.assertRaises(OpportunityError):
            evaluate_opportunity(opportunity(commission_pct=float("inf")))

    def test_unknown_fields_and_duplicate_ids_are_rejected(self):
        with self.assertRaises(OpportunityError):
            evaluate_opportunity(opportunity(unreviewed_cost_xof=100))
        with self.assertRaises(OpportunityError):
            rank_opportunities([opportunity("same"), opportunity("same")])

    def test_negative_cash_cost_is_rejected(self):
        with self.assertRaises(OpportunityError):
            evaluate_opportunity(opportunity(delivery_cost_xof=-1))


if __name__ == "__main__":
    unittest.main()
