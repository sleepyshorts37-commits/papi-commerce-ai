import unittest

from runtime.papi_core.financial_control import build_financial_control


class FinancialControlTests(unittest.TestCase):
    def setUp(self):
        self.entries = [
            {"entry_ref": "E1", "account": "Wave", "direction": "inflow",
             "category": "sale", "amount_xof": 25000, "status": "verified",
             "occurred_at": "2026-11-10T10:00:00Z", "payment_method": "wave"},
            {"entry_ref": "E2", "account": "Wave", "direction": "outflow",
             "category": "operating_expense", "amount_xof": 5000, "status": "verified",
             "occurred_at": "2026-11-10T11:00:00Z", "payment_method": "wave"},
            {"entry_ref": "E3", "account": "Wave", "direction": "inflow",
             "category": "sale", "amount_xof": 9000, "status": "pending",
             "occurred_at": "2026-11-11T10:00:00Z", "payment_method": "wave"},
        ]

    def test_verified_balance_excludes_pending(self):
        result = build_financial_control(self.entries, opening_balances={"Wave": 1000})
        balance = result["balances_by_account"]["Wave"]
        self.assertEqual(balance["calculated_verified_balance_xof"], 21000)
        self.assertEqual(balance["pending_inflow_excluded_xof"], 9000)
        self.assertEqual(result["totals"]["verified_net_cash_movement_xof"], 20000)

    def test_reconciliation_match_and_mismatch(self):
        result = build_financial_control(self.entries, opening_balances={"Wave": 1000},
                                         provider_balances={"Wave": 21000, "Orange Money": 0})
        self.assertEqual(result["balances_by_account"]["Wave"]["reconciliation_status"], "matched")
        self.assertEqual(result["balances_by_account"]["Orange Money"]["reconciliation_status"], "matched")
        mismatch = build_financial_control(self.entries, provider_balances={"Wave": 999})
        self.assertEqual(mismatch["balances_by_account"]["Wave"]["reconciliation_status"], "mismatch")

    def test_rejects_unknown_fields_and_invalid_amounts(self):
        bad = [{**self.entries[0], "amount_xof": -1},
               {**self.entries[0], "entry_ref": "E4", "customer_phone": "770000000"}]
        result = build_financial_control(bad)
        self.assertEqual(result["entries_analyzed"], 0)
        self.assertEqual(result["entries_rejected"], 2)

    def test_duplicate_entry_reference_rejected(self):
        result = build_financial_control([self.entries[0], self.entries[0]])
        self.assertEqual(result["entries_analyzed"], 1)
        self.assertEqual(result["entries_rejected"], 1)

    def test_commission_payouts_are_tracked_not_executed(self):
        entry = {**self.entries[1], "entry_ref": "C1", "category": "commission_payout"}
        result = build_financial_control([entry])
        self.assertEqual(result["commission_tracking"]["verified_commission_payouts_xof"], 5000)
        self.assertEqual(result["controls"]["commissions_paid"], 0)
        self.assertEqual(result["controls"]["payments_processed"], 0)

    def test_declared_and_pending_do_not_change_cash(self):
        rows = [{**self.entries[0], "status": "declared"}]
        result = build_financial_control(rows)
        self.assertEqual(result["totals"]["verified_inflow_xof"], 0)
        self.assertEqual(result["totals"]["pending_inflow_xof"], 25000)
        self.assertEqual(result["controls"]["transfers_executed"], 0)


if __name__ == "__main__":
    unittest.main()
