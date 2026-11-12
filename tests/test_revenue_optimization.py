import unittest

from runtime.papi_core.revenue_optimization import optimize_revenue


BASE = {
    "offer_name": "Pack test", "business_line": "PAPI MARKET", "market": "Senegal",
    "currency": "XOF", "selling_price_xof": 10000, "unit_variable_cost_xof": 6000,
}


class RevenueOptimizationTests(unittest.TestCase):
    def test_unit_economics_break_even_and_target(self):
        row = optimize_revenue([{**BASE, "fixed_cost_xof": 12000, "fixed_cost_period": "month",
                                 "target_sales_count": 10}])["offers"][0]
        self.assertEqual(row["unit_contribution_xof"], 4000)
        self.assertEqual(row["break_even_units"], 3)
        self.assertEqual(row["target_gross_revenue_xof"], 100000)
        self.assertEqual(row["target_contribution_after_commission_xof"], 28000)
        self.assertEqual(row["target_status"], "hypothetical_planning_not_forecast")

    def test_unverified_sales_never_become_revenue(self):
        row = optimize_revenue([{**BASE, "sales_count": 12}])["offers"][0]
        self.assertIsNone(row["realized_revenue_xof"])
        self.assertEqual(row["realized_revenue_status"], "unknown_unverified")

    def test_verified_paid_revenue_requires_explicit_fields(self):
        result = optimize_revenue([{**BASE, "payment_verification_status": "verified"}])
        self.assertEqual(result["offers_rejected"], 1)
        row = optimize_revenue([{**BASE, "payment_verification_status": "verified",
                                 "verified_paid_units": 2, "verified_paid_revenue_xof": 20000,
                                 "commission_rate_bps": 500}])["offers"][0]
        self.assertEqual(row["realized_revenue_xof"], 20000)
        self.assertEqual(row["realized_commission_xof"], 1000)

    def test_commission_and_basis_point_validation(self):
        row = optimize_revenue([{**BASE, "commission_rate_bps": 1000,
                                 "commission_fixed_xof": 100}])["offers"][0]
        self.assertEqual(row["commission_per_unit_xof"], 1100)
        self.assertEqual(row["net_contribution_after_commission_xof"], 2900)
        self.assertEqual(optimize_revenue([{**BASE, "commission_rate_bps": 10001}])["offers_rejected"], 1)

    def test_missing_fixed_cost_and_below_cost_price(self):
        row = optimize_revenue([{**BASE, "selling_price_xof": 5000,
                                 "alternative_prices_xof": [5000, 7000]}])["offers"][0]
        self.assertIsNone(row["break_even_units"])
        self.assertEqual(row["break_even_status"], "unknown_missing_fixed_cost")
        self.assertEqual(row["price_warning"], "selling_price_below_variable_cost")
        self.assertTrue(row["price_scenarios"][0]["below_variable_cost"])

    def test_currency_validation_and_read_only(self):
        result = optimize_revenue([{**BASE, "currency": "EUR"}])
        self.assertEqual(result["offers_rejected"], 1)
        self.assertEqual(result["controls"]["payments_processed"], 0)
        self.assertTrue(result["controls"]["read_only"])


if __name__ == "__main__":
    unittest.main()
