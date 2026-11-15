import unittest
from papi_core.kids_profitability import KidsProfitabilityError,evaluate_offer

def offer():
    def amount(v,c="XOF"): return {"value":str(v),"currency":c,"source":"synthetic test fixture, not market data","observed_at":"2026-11-15"}
    def rate(v): return {"value":str(v),"currency":"RATE","source":"synthetic test fixture","observed_at":"2026-11-15"}
    return {"schema_version":1,"book_id":"PKP-TEST","platform_id":"test_platform","channel_status":"ELIGIBLE_ZERO_UPFRONT","seller_funds_before_payout":False,"currency":"XOF",
    "sale_price":amount("10000"),"printing_cost":amount("3000"),"distribution_fee":amount("500"),"shipping_cost":amount("0"),"taxes":amount("0"),"withholding":amount("0"),"fixed_cost_per_copy":amount("500"),"upfront_cost":amount("0"),
    "platform_commission_rate":rate("0.10"),"payment_fee_rate":rate("0.02"),"fx_to_xof":None}

class KidsProfitabilityTests(unittest.TestCase):
    def test_exact_unit_economics(self):
        r=evaluate_offer(offer()); self.assertEqual(r["platform_commission"],"1000.00"); self.assertEqual(r["payment_fee"],"200.00"); self.assertEqual(r["net_per_copy"],"4800.00"); self.assertEqual(r["break_even_sale_price"],"4545.45"); self.assertTrue(r["channel_eligible_for_commercial_comparison"])
    def test_missing_cost_rejected(self):
        d=offer(); del d["shipping_cost"]
        with self.assertRaises(KidsProfitabilityError): evaluate_offer(d)
    def test_positive_upfront_disqualifies(self):
        d=offer(); d["upfront_cost"]["value"]="1"; r=evaluate_offer(d); self.assertFalse(r["zero_upfront_policy_passed"]); self.assertFalse(r["channel_eligible_for_commercial_comparison"])
    def test_seller_advance_disqualifies(self):
        d=offer(); d["seller_funds_before_payout"]=True; self.assertFalse(evaluate_offer(d)["channel_eligible_for_commercial_comparison"])
    def test_hold_channel_never_recommended(self):
        d=offer(); d["channel_status"]="HOLD"; self.assertEqual(evaluate_offer(d)["commercial_decision"],"HOLD_OR_BLOCKED_NO_RECOMMENDATION")
    def test_null_unknown_cost_rejected(self):
        d=offer(); d["printing_cost"]=None
        with self.assertRaises(KidsProfitabilityError): evaluate_offer(d)
    def test_currency_mismatch_rejected(self):
        d=offer(); d["printing_cost"]["currency"]="EUR"
        with self.assertRaises(KidsProfitabilityError): evaluate_offer(d)
    def test_fx_conversion_and_date(self):
        d=offer(); d["currency"]="EUR"
        for k in ("sale_price","printing_cost","distribution_fee","shipping_cost","taxes","withholding","fixed_cost_per_copy","upfront_cost"): d[k]["currency"]="EUR"
        d["fx_to_xof"]={"value":"655.957","source":"documented synthetic fixture","observed_at":"2026-11-15"}
        self.assertEqual(evaluate_offer(d)["xof"]["sale_price"],"6559570.00")
        d["fx_to_xof"]["observed_at"]="2026-02-30"
        with self.assertRaises(KidsProfitabilityError): evaluate_offer(d)
    def test_impossible_date_and_negative_value_rejected(self):
        d=offer(); d["taxes"]["observed_at"]="2026-02-30"
        with self.assertRaises(KidsProfitabilityError): evaluate_offer(d)
        d=offer(); d["sale_price"]["value"]="-1"
        with self.assertRaises(KidsProfitabilityError): evaluate_offer(d)
    def test_rate_over_100_percent_rejected(self):
        d=offer(); d["platform_commission_rate"]["value"]="1.2"
        with self.assertRaises(KidsProfitabilityError): evaluate_offer(d)
    def test_zero_price_margin_is_none(self):
        d=offer(); d["sale_price"]["value"]="0"; self.assertIsNone(evaluate_offer(d)["net_margin_rate"])

if __name__=="__main__": unittest.main()
