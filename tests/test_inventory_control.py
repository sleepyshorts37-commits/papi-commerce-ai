import unittest
from papi_core.inventory_control import build_inventory_control

def move(mid,kind,qty):
    return {"movement_id":mid,"sku":"SKU-1","product_name":"Article","location":"Dakar","kind":kind,"quantity":qty,"occurred_at":"2026-11-12T10:00:00Z"}

class InventoryTests(unittest.TestCase):
    def test_receipt_sale_and_available_stock(self):
        r=build_inventory_control([move("1","receipt",20),move("2","sale",5)],reorder_points={"SKU-1":10})
        s=r["stock_by_sku"]["SKU-1"]
        self.assertEqual(s["on_hand"],15); self.assertEqual(s["available"],15); self.assertEqual(s["status"],"sufficient")
    def test_reservations_reduce_available_not_on_hand(self):
        r=build_inventory_control([move("1","receipt",12),move("2","reserve",5)])
        s=r["stock_by_sku"]["SKU-1"]
        self.assertEqual(s["on_hand"],12); self.assertEqual(s["reserved"],5); self.assertEqual(s["available"],7)
    def test_release_and_sale(self):
        r=build_inventory_control([move("1","receipt",12),move("2","reserve",5),move("3","release",2),move("4","sale",3)])
        self.assertEqual(r["stock_by_sku"]["SKU-1"]["available"],6)
    def test_insufficient_stock_movement_rejected(self):
        r=build_inventory_control([move("1","sale",2)])
        self.assertEqual(r["movements_rejected"],1); self.assertEqual(r["stock_by_sku"]["SKU-1"]["on_hand"],0)
    def test_replenishment_suggestion_is_not_order(self):
        r=build_inventory_control([move("1","receipt",4)],reorder_points={"SKU-1":5},target_stock={"SKU-1":15})
        self.assertEqual(r["replenishment_alerts"][0]["suggested_replenishment_quantity"],11)
        self.assertEqual(r["controls"]["orders_created"],0)
    def test_duplicate_movement_id_rejected(self):
        m=move("same","receipt",3); r=build_inventory_control([m,dict(m)])
        self.assertEqual(r["movements_analyzed"],1); self.assertEqual(r["movements_rejected"],1)
    def test_invalid_timestamp_rejected(self):
        m=move("1","receipt",3); m["occurred_at"]="2026-11-12"
        self.assertEqual(build_inventory_control([m])["movements_rejected"],1)
    def test_target_requires_reorder_point(self):
        with self.assertRaises(ValueError): build_inventory_control([],target_stock={"SKU-1":10})

if __name__=="__main__": unittest.main()
