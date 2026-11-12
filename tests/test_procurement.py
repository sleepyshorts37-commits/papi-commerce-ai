import unittest
from papi_core.procurement import analyze_procurement

def observation(**overrides):
    row = {"supplier_id":"S-1","supplier_name":"Fournisseur A","product_key":"phone-case","product_name":"Coque téléphone","market":"Senegal","currency":"XOF","unit_price_xof":1000,"minimum_order_quantity":10,"shipping_total_xof":5000,"shipping_allocation_units":10,"taxes_total_xof":1000,"packaging_per_unit_xof":100,"other_fees_total_xof":0,"lead_time_days":5,"observed_at":"2026-11-12T10:00:00Z","source_ref":"https://example.com/product","completed_orders":20,"on_time_orders":18,"inspected_units":100,"defective_units":2,"documented_disputes":1}
    row.update(overrides); return row

class ProcurementTests(unittest.TestCase):
    def test_complete_landed_cost_and_evidence_rates(self):
        row=analyze_procurement([observation()],as_of="2026-11-12T11:00:00Z")["observations"][0]
        self.assertEqual(row["landed_unit_cost_xof"],1700); self.assertEqual(row["on_time_rate_percent"],90.0); self.assertEqual(row["defect_rate_percent"],2.0)
    def test_incomplete_cost_stays_unknown(self):
        row=observation(); del row["shipping_total_xof"]
        out=analyze_procurement([row],as_of="2026-11-12T11:00:00Z")["observations"][0]
        self.assertIsNone(out["landed_unit_cost_xof"])
    def test_stale_not_ranked(self):
        out=analyze_procurement([observation(observed_at="2026-09-01T00:00:00Z")],as_of="2026-11-12T11:00:00Z")
        self.assertEqual(out["comparisons"],[]); self.assertEqual(out["observations"][0]["evidence_status"],"stale")
    def test_duplicate_deduplicated(self):
        row=observation(); out=analyze_procurement([row,dict(row)],as_of="2026-11-12T11:00:00Z")
        self.assertEqual(out["observations_analyzed"],1)
    def test_comparable_options_ranked_by_landed_cost(self):
        out=analyze_procurement([observation(),observation(supplier_id="S-2",supplier_name="B",unit_price_xof=900)],as_of="2026-11-12T11:00:00Z")
        self.assertEqual(out["comparisons"][0]["suppliers"][0]["supplier_id"],"S-2")
    def test_missing_reliability_is_unknown(self):
        row=observation()
        for f in ("completed_orders","on_time_orders","inspected_units","defective_units","documented_disputes"): row.pop(f)
        out=analyze_procurement([row],as_of="2026-11-12T11:00:00Z")
        self.assertEqual(out["observations"][0]["reliability_status"],"unknown")
    def test_bad_currency_and_non_https_rejected(self):
        out=analyze_procurement([observation(currency="USD"),observation(supplier_id="S-2",source_ref="http://example.com")],as_of="2026-11-12T11:00:00Z")
        self.assertEqual(out["observations_rejected"],2)
    def test_no_purchase_or_spending(self):
        c=analyze_procurement([observation()],as_of="2026-11-12T11:00:00Z")["controls"]
        self.assertEqual(c["purchase_orders_created"],0); self.assertEqual(c["spending_xof"],0); self.assertEqual(c["suppliers_contacted"],0)

if __name__=="__main__": unittest.main()
