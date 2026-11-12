import unittest
from runtime.papi_core.services_mvp import analyze_services

class ServicesMvpTests(unittest.TestCase):
    def setUp(self):
        self.requests=[{"request_id":"R1","service_code":"WHATSAPP_ASSISTANT","scope_summary":"Configuration et support","status":"qualified","created_at":"2026-11-01T09:00:00Z"}]
        self.quotes=[{"quote_id":"Q1","request_id":"R1","amount_xof":15000,"valid_until":"2026-12-01T00:00:00Z","status":"accepted"}]
        self.work=[{"work_id":"W1","quote_id":"Q1","status":"delivered","started_at":"2026-11-02T09:00:00Z","updated_at":"2026-11-03T09:00:00Z","delivered_at":"2026-11-03T08:00:00Z"}]
        self.payments=[{"payment_id":"P1","work_id":"W1","amount_xof":15000,"status":"provider_verified","evidence_ref":"TX-123","verified_by":"human-review","verified_at":"2026-11-03T10:00:00Z"}]
    def report(self,**changes):
        args={"requests":self.requests,"quotes":self.quotes,"work_items":self.work,"payments":self.payments,"as_of":"2026-11-04T00:00:00Z"}
        args.update(changes); return analyze_services(**args)
    def test_verified_revenue_counted(self):
        self.assertEqual(self.report()["revenue"]["recognized_xof"],15000)
    def test_declared_payment_not_revenue(self):
        p=dict(self.payments[0],status="declared_paid")
        r=self.report(payments=[p]); self.assertEqual(r["revenue"]["recognized_xof"],0); self.assertEqual(r["revenue"]["unverified_declared_xof"],15000)
    def test_evidence_required_for_verified_payment(self):
        p=dict(self.payments[0],evidence_ref="")
        r=self.report(payments=[p]); self.assertEqual(r["counts"]["rejected_records"],1); self.assertEqual(r["revenue"]["recognized_xof"],0)
    def test_personal_data_rejected(self):
        r=self.report(requests=[dict(self.requests[0],customer_phone="+221700000000")])
        self.assertEqual(r["counts"]["requests"],0); self.assertEqual(r["counts"]["rejected_records"],1)
    def test_unknown_quote_reference_rejected(self):
        r=self.report(quotes=[dict(self.quotes[0],request_id="MISSING")]); self.assertEqual(r["counts"]["quotes"],0)
    def test_duplicate_request_rejected(self):
        r=self.report(requests=self.requests*2); self.assertEqual(r["counts"]["requests"],1); self.assertEqual(r["counts"]["rejected_records"],1)
    def test_unsupported_currency_rejected(self):
        r=self.report(quotes=[dict(self.quotes[0],currency="USD")]); self.assertEqual(r["counts"]["quotes"],0)
    def test_delivered_work_requires_timestamp(self):
        r=self.report(work_items=[dict(self.work[0],delivered_at=None)]); self.assertEqual(r["counts"]["work_items"],0)
    def test_read_only_zero_budget(self):
        s=self.report()["safety"]; self.assertEqual(s["budget_xof"],0); self.assertFalse(s["external_actions"]); self.assertFalse(s["financial_actions"])

if __name__=="__main__": unittest.main()
