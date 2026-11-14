import unittest
from decimal import Decimal

from papi_core.profitability import (
    ProfitabilityError, evaluate_offer_profitability, rank_offer_profitability,
)


def offer(**overrides):
    value = {
        "offer_id": "task-001",
        "currency": "USD",
        "gross_revenue": "100",
        "platform_fee": "10",
        "payout_fee": "2",
        "infrastructure_cost": "3",
        "other_cost": "5",
        "estimated_hours": "4",
        "labor_hourly_rate": "10",
        "minimum_net_hourly_rate": "8",
        "minimum_margin_percent": "10",
    }
    if "target_hourly_rate" in overrides and "minimum_net_hourly_rate" not in overrides:
        value.pop("minimum_net_hourly_rate")
    value.update(overrides)
    return value


class ProfitabilityTests(unittest.TestCase):
    def test_net_profit_includes_all_fees_costs_and_labor(self):
        result = evaluate_offer_profitability(offer())
        self.assertEqual(result["estimated_net_profit_after_labor"], "40.00")
        self.assertEqual(result["estimated_net_hourly_rate"], "10.00")
        self.assertEqual(result["status"], "viable_for_human_review")

    def test_loss_making_offer_is_flagged(self):
        result = evaluate_offer_profitability(offer(gross_revenue="20"))
        self.assertEqual(result["status"], "loss_making")

    def test_hourly_target_is_enforced(self):
        result = evaluate_offer_profitability(offer(target_hourly_rate="12"))
        self.assertEqual(result["status"], "below_hourly_target")

    def test_legacy_target_hourly_rate_alias_is_supported(self):
        result = evaluate_offer_profitability(offer(target_hourly_rate="12"))
        self.assertEqual(result["minimum_net_hourly_rate"], "12.00")
        self.assertEqual(result["status"], "below_hourly_target")

    def test_conflicting_hourly_threshold_aliases_are_rejected(self):
        with self.assertRaises(ProfitabilityError):
            evaluate_offer_profitability(offer(target_hourly_rate="12", minimum_net_hourly_rate="8"))

    def test_minimum_margin_is_enforced(self):
        result = evaluate_offer_profitability(offer(minimum_margin_percent="50"))
        self.assertEqual(result["status"], "below_minimum_margin")

    def test_zero_revenue_is_not_divided_by_zero(self):
        result = evaluate_offer_profitability(offer(gross_revenue="0"))
        self.assertEqual(result["status"], "loss_making")

    def test_negative_or_non_finite_amount_is_rejected(self):
        for bad in ("-1", "NaN", "Infinity", True):
            with self.subTest(bad=bad), self.assertRaises(ProfitabilityError):
                evaluate_offer_profitability(offer(other_cost=bad))

    def test_zero_hours_is_rejected(self):
        with self.assertRaises(ProfitabilityError):
            evaluate_offer_profitability(offer(estimated_hours="0"))

    def test_currency_code_is_required(self):
        with self.assertRaises(ProfitabilityError):
            evaluate_offer_profitability(offer(currency="FCFA"))

    def test_currency_is_not_converted_and_no_spending_is_authorized(self):
        result = evaluate_offer_profitability(offer(currency="XOF"))
        self.assertFalse(result["currency_conversion_performed"])
        self.assertFalse(result["spending_authorized"])
        self.assertFalse(result["external_actions_performed"])

    def test_rank_orders_by_net_hourly_return(self):
        result = rank_offer_profitability([
            offer(offer_id="lower", gross_revenue="80"),
            offer(offer_id="higher", gross_revenue="200", estimated_hours="2"),
        ])
        self.assertEqual(result["results"][0]["offer_id"], "higher")
        self.assertEqual(result["results"][0]["rank"], 1)

    def test_invalid_batch_is_rejected(self):
        with self.assertRaises(ProfitabilityError):
            rank_offer_profitability("not-a-list")


if __name__ == "__main__":
    unittest.main()
