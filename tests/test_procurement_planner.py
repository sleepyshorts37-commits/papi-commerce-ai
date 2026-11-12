import unittest
from runtime.papi_core.procurement_planner import plan_replenishment
class ProcurementPlannerTests(unittest.TestCase):
 def setUp(self):
  self.s=[{"supplier_id":"S1","display_name":"Supplier A","status":"approved","lead_time_days":4,"minimum_order_quantity":2}]
  self.p=[{"product_id":"P1","sku":"SKU1","display_name":"Product A","supplier_id":"S1","quantity_on_hand":2,"reorder_level":5,"target_stock":12,"unit_cost_xof":500,"status":"active"}]
 def test_proposal(self):
  x=plan_replenishment(self.p,self.s,budget_xof=6000)["proposals"][0]; self.assertEqual(x["suggested_quantity"],10); self.assertEqual(x["estimated_total_xof"],5000); self.assertEqual(x["decision"],"awaiting_human_approval")
 def test_inactive_product(self):
  self.assertEqual(plan_replenishment([dict(self.p[0],status="inactive")],self.s)["proposals"],[])
 def test_unapproved_supplier(self):
  self.assertEqual(plan_replenishment(self.p,[dict(self.s[0],status="prospect")])["proposals"],[])
 def test_unknown_supplier(self):
  self.assertEqual(plan_replenishment([dict(self.p[0],supplier_id="X")],self.s)["counts"]["rejected_records"],1)
 def test_minimum_order(self):
  p=dict(self.p[0],quantity_on_hand=5,target_stock=6); self.assertEqual(plan_replenishment([p],self.s)["proposals"][0]["suggested_quantity"],2)
 def test_budget_advisory(self):
  x=plan_replenishment(self.p,self.s,budget_xof=100)["proposals"][0]; self.assertFalse(x["within_configured_budget"])
 def test_personal_field(self):
  self.assertEqual(plan_replenishment(self.p,[dict(self.s[0],phone="private")])["counts"]["proposals"],0)
 def test_duplicate_product(self):
  r=plan_replenishment(self.p*2,self.s); self.assertEqual(r["counts"]["proposals"],1); self.assertEqual(r["counts"]["rejected_records"],1)
 def test_negative_stock_rejected(self):
  self.assertEqual(plan_replenishment([dict(self.p[0],quantity_on_hand=-1)],self.s)["counts"]["proposals"],0)
 def test_no_side_effects(self):
  z=plan_replenishment(self.p,self.s)["safety"]; self.assertTrue(z["read_only"]); self.assertFalse(z["purchase_orders_created"]); self.assertFalse(z["payments"]); self.assertEqual(z["budget_xof"],0)
if __name__=="__main__": unittest.main()
