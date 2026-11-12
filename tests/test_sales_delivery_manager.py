import unittest
from datetime import datetime, timezone
from runtime.papi_core.sales_delivery_manager import analyze_sales_delivery

NOW=datetime.now(timezone.utc).replace(microsecond=0).isoformat()
class SalesDeliveryTests(unittest.TestCase):
 def setUp(self):
  self.sales=[{"sale_id":"SA1","order_id":"O1","business_unit":"PAPI MARKET","amount_xof":12000,"currency":"XOF","payment_status":"payment_declared","created_at":NOW}]
  self.deliveries=[{"delivery_id":"D1","order_id":"O1","status":"delivered","created_at":NOW,"updated_at":NOW,"delivered_at":NOW}]
 def test_reconciles_delivered_sale(self):
  r=analyze_sales_delivery(self.sales,self.deliveries); self.assertEqual(r["counts"]["delivered_orders"],1); self.assertEqual(r["financial"]["gross_declared_sales_xof"],12000)
 def test_unlinked_delivery_rejected(self):
  d=dict(self.deliveries[0],order_id="unknown"); self.assertEqual(analyze_sales_delivery(self.sales,[d])["counts"]["rejected_records"],1)
 def test_delivered_requires_timestamp(self):
  d=dict(self.deliveries[0],delivered_at=None); self.assertEqual(analyze_sales_delivery(self.sales,[d])["counts"]["deliveries"],0)
 def test_personal_data_rejected(self):
  s=dict(self.sales[0],phone="+221700000000"); self.assertEqual(analyze_sales_delivery([s],[])["counts"]["sales"],0)
 def test_duplicate_delivery_rejected(self):
  r=analyze_sales_delivery(self.sales,self.deliveries*2); self.assertEqual(r["counts"]["deliveries"],1); self.assertEqual(r["counts"]["rejected_records"],1)
 def test_declared_payment_not_recognized_revenue(self):
  f=analyze_sales_delivery(self.sales,[])["financial"]; self.assertEqual(f["payment_declared_xof"],12000); self.assertEqual(f["recognized_revenue_xof"],0)
 def test_failed_delivery_requires_code(self):
  d=dict(self.deliveries[0],status="failed",delivered_at=None,failure_code=None); self.assertEqual(analyze_sales_delivery(self.sales,[d])["counts"]["deliveries"],0)
 def test_future_date_rejected(self):
  d=dict(self.deliveries[0],updated_at="2999-01-01T00:00:00+00:00"); self.assertEqual(analyze_sales_delivery(self.sales,[d])["counts"]["deliveries"],0)
 def test_safety_read_only(self):
  s=analyze_sales_delivery(self.sales,self.deliveries)["safety"]; self.assertTrue(s["read_only"]); self.assertFalse(s["payments_or_refunds"]); self.assertEqual(s["budget_xof"],0)
if __name__=="__main__": unittest.main()
