import unittest
from runtime.papi_core.executive_dashboard import build_executive_dashboard
class ExecutiveDashboardTests(unittest.TestCase):
 def test_empty_dashboard_safe(self):
  r=build_executive_dashboard(); self.assertEqual(r["finance"]["recognized_revenue_xof"],0); self.assertTrue(r["safety"]["read_only"])
 def test_aggregates_snapshots(self):
  r=build_executive_dashboard(sales_delivery={"counts":{"sales":4,"deliveries":3,"delivered_orders":2,"sales_without_delivery":1},"financial":{"gross_declared_sales_xof":20000}},financial={"counts":{"matched":2,"unmatched_transactions":1},"declared_totals":{"incoming_xof":15000,"outgoing_xof":5000}},inventory={"counts":{"products":8,"low_stock":2,"negative_stock":0}},procurement={"counts":{"proposals":2}},services={"counts":{"requests":5,"open_cases":1}})
  self.assertEqual(r["finance"]["net_declared_cashflow_xof"],10000); self.assertEqual(r["commercial"]["sales_without_delivery"],1); self.assertEqual(r["operations"]["low_stock_items"],2); self.assertEqual(r["operations"]["replenishment_proposals"],2)
 def test_missing_snapshots_reported(self):
  self.assertIn("inventory",build_executive_dashboard()["data_quality"]["missing_snapshots"])
 def test_never_recognizes_revenue(self):
  r=build_executive_dashboard(financial={"declared_totals":{"incoming_xof":999999}}); self.assertEqual(r["finance"]["recognized_revenue_xof"],0); self.assertFalse(r["finance"]["provider_authenticated"])
 def test_rejects_bad_snapshot(self):
  with self.assertRaises(ValueError): build_executive_dashboard(sales_delivery="bad")
 def test_rejects_negative_metric(self):
  with self.assertRaises(ValueError): build_executive_dashboard(financial={"declared_totals":{"incoming_xof":-1}})
 def test_no_external_actions(self):
  s=build_executive_dashboard()["safety"]; self.assertFalse(s["external_actions"]); self.assertFalse(s["payments_or_transfers"]); self.assertEqual(s["budget_xof"],0)
if __name__=="__main__": unittest.main()
