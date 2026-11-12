import unittest
from runtime.papi_core.services_operations_board import build_services_operations_board

NOW="2026-11-12T12:00:00+00:00"
class ServicesOperationsBoardTests(unittest.TestCase):
 def base(self):
  req=[{"request_id":"R1","service_code":"WHATSAPP_ASSISTANT_BASIC","scope_summary":"Assistant de réponses","status":"qualified","created_at":"2026-11-10T10:00:00Z"}]
  quote=[{"quote_id":"Q1","request_id":"R1","amount_xof":10000,"currency":"XOF","valid_until":"2026-11-20T00:00:00Z","status":"accepted"}]
  work=[{"work_id":"W1","quote_id":"Q1","status":"delivered","started_at":"2026-11-10T10:00:00Z","updated_at":"2026-11-11T10:00:00Z","delivered_at":"2026-11-11T09:00:00Z"}]
  return req,quote,work,[]
 def test_accepted_quote_without_work_creates_delivery_task(self):
  r,q,w,p=self.base(); w=[]
  out=build_services_operations_board(requests=r,quotes=q,work_items=w,payments=p,as_of=NOW)
  self.assertEqual(out["tasks"][0]["type"],"schedule_delivery")
 def test_delivered_unpaid_creates_reconciliation_task(self):
  r,q,w,p=self.base()
  out=build_services_operations_board(requests=r,quotes=q,work_items=w,payments=p,as_of=NOW)
  self.assertEqual(out["tasks"][0]["type"],"reconcile_payment")
 def test_new_request_creates_qualification_task(self):
  r,q,w,p=self.base(); q=[]; w=[]; r[0]["status"]="new"
  out=build_services_operations_board(requests=r,quotes=q,work_items=w,payments=p,as_of=NOW)
  self.assertEqual(out["tasks"][0]["type"],"qualify_request")
 def test_rejects_work_without_accepted_quote(self):
  r,q,w,p=self.base(); q[0]["status"]="draft"
  out=build_services_operations_board(requests=r,quotes=q,work_items=w,payments=p,as_of=NOW)
  self.assertEqual(out["counts"]["work_items"],0)
  self.assertGreater(out["counts"]["rejected_records"],0)
 def test_rejects_personal_contact_fields(self):
  r,q,w,p=self.base(); r[0]["phone"]="+221..."
  out=build_services_operations_board(requests=r,quotes=q,work_items=w,payments=p,as_of=NOW)
  self.assertEqual(out["counts"]["requests"],0)
 def test_no_automatic_external_or_financial_actions(self):
  r=build_services_operations_board(requests=[],quotes=[],work_items=[],payments=[],as_of=NOW)
  self.assertTrue(r["safety"]["read_only"]); self.assertFalse(r["safety"]["messages_sent"])
  self.assertFalse(r["safety"]["payments_or_transfers"]); self.assertEqual(r["safety"]["budget_xof"],0)
 def test_payment_attestation_does_not_recognize_revenue(self):
  r,q,w,p=self.base(); p=[{"payment_id":"P1","work_id":"W1","amount_xof":10000,"status":"provider_verified","evidence_ref":"ref","verified_by":"operator","verified_at":"2026-11-11T11:00:00Z"}]
  out=build_services_operations_board(requests=r,quotes=q,work_items=w,payments=p,as_of=NOW)
  self.assertEqual(out["safety"]["recognized_revenue_xof"],0)
  self.assertEqual(out["tasks"][0]["type"],"verify_provider_evidence")
if __name__=="__main__": unittest.main()
