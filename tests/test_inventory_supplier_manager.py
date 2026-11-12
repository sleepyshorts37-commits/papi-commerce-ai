import unittest
from runtime.papi_core.inventory_supplier_manager import analyze_inventory

class InventorySupplierTests(unittest.TestCase):
    def setUp(self):
        self.suppliers=[{"supplier_id":"S1","display_name":"Supplier A","category":"general","status":"approved","lead_time_days":3,"payment_terms":"cash"}]
        self.products=[{"product_id":"P1","sku":"SKU1","display_name":"Item A","supplier_id":"S1","unit_cost_xof":500,"reorder_level":5,"status":"active"}]
        self.movements=[{"movement_id":"M1","product_id":"P1","kind":"in","quantity":10,"occurred_at":"2026-11-01T10:00:00Z","reference":"INV-1"}]
    def report(self,**kw):
        data={"suppliers":self.suppliers,"products":self.products,"movements":self.movements,"as_of":"2026-11-12T12:00:00Z"}
        data.update(kw); return analyze_inventory(**data)
    def test_stock_balance(self):
        self.assertEqual(self.report()["stock"]["balances"][0]["quantity_on_hand"],10)
    def test_outgoing_movement(self):
        out=dict(self.movements[0],movement_id="M2",kind="out",quantity=7)
        self.assertEqual(self.report(movements=self.movements+[out])["stock"]["balances"][0]["quantity_on_hand"],3)
    def test_low_stock_alert(self):
        self.assertEqual(self.report(movements=[])["stock"]["low_stock_product_ids"],["P1"])
    def test_unknown_supplier_rejected(self):
        p=dict(self.products[0],supplier_id="MISSING")
        report=self.report(products=[p])
        self.assertEqual(report["counts"]["rejected_records"],2)
        self.assertEqual([x["category"] for x in report["rejected"]],["product","movement"])
    def test_personal_field_rejected(self):
        s=dict(self.suppliers[0],phone="+221700000000")
        report=self.report(suppliers=[s])
        self.assertEqual(report["counts"]["rejected_records"],3)
        self.assertEqual([x["category"] for x in report["rejected"]],["supplier","product","movement"])
    def test_duplicate_movement_rejected(self):
        self.assertEqual(self.report(movements=self.movements*2)["counts"]["rejected_records"],1)
    def test_future_movement_rejected(self):
        m=dict(self.movements[0],occurred_at="2026-12-01T10:00:00Z")
        self.assertEqual(self.report(movements=[m])["counts"]["rejected_records"],1)
    def test_negative_stock_visible(self):
        m=dict(self.movements[0],kind="out",quantity=12)
        self.assertEqual(self.report(movements=[m])["stock"]["negative_stock_product_ids"],["P1"])
    def test_zero_budget_read_only(self):
        safety=self.report()["safety"]
        self.assertTrue(safety["read_only"]); self.assertEqual(safety["budget_xof"],0)
        self.assertFalse(safety["purchase_orders"])

if __name__=="__main__": unittest.main()
