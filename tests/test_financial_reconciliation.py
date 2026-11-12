import unittest
from datetime import datetime, timezone
from runtime.papi_core.financial_reconciliation import reconcile_finances
NOW=datetime.now(timezone.utc).replace(microsecond=0).isoformat()
class FinancialReconciliationTests(unittest.TestCase):
 def setUp(self):
  self.tx=[{"transaction_id":"T1","reference":"REF1","direction":"in","amount_xof":10000,"status":"declared","occurred_at":NOW,"source":"operator"}]
  self.st=[{"statement_id":"S1","reference":"REF1","direction":"in","amount_xof":10000,"occurred_at":NOW}]
 def test_matches_exact_reference_direction_amount(self):
  r=reconcile_finances(self.tx,self.st); self.assertEqual(r["counts"]["matched"],1); self.assertEqual(r["declared_totals"]["incoming_xof"],10000)
 def test_unmatched_statement_reported(self):
  r=reconcile_finances(self.tx,[]); self.assertEqual(r["counts"]["unmatched_transactions"],1)
 def test_ambiguous_statement_not_auto_matched(self):
  r=reconcile_finances(self.tx,[self.st[0],dict(self.st[0],statement_id="S2")]); self.assertEqual(r["counts"]["matched"],0); self.assertEqual(r["unmatched_transactions"][0]["reason"],"ambiguous_statement_match")
 def test_cancelled_transaction_not_matched(self):
  t=dict(self.tx[0],status="cancelled"); self.assertEqual(reconcile_finances([t],self.st)["counts"]["matched"],0)
 def test_personal_fields_rejected(self):
  t=dict(self.tx[0],phone="private"); self.assertEqual(reconcile_finances([t],self.st)["counts"]["transactions"],0)
 def test_duplicate_transaction_id_rejected(self):
  r=reconcile_finances(self.tx*2,self.st); self.assertEqual(r["counts"]["transactions"],1); self.assertEqual(r["counts"]["rejected_records"],1)
 def test_wrong_amount_does_not_match(self):
  s=dict(self.st[0],amount_xof=9999); self.assertEqual(reconcile_finances(self.tx,[s])["counts"]["matched"],0)
 def test_naive_timestamp_rejected(self):
  t=dict(self.tx[0],occurred_at="2026-01-01T12:00:00"); self.assertEqual(reconcile_finances([t],self.st)["counts"]["transactions"],0)
 def test_revenue_never_claimed_as_verified(self):
  r=reconcile_finances(self.tx,self.st); self.assertEqual(r["declared_totals"]["recognized_revenue_xof"],0); self.assertFalse(r["safety"]["provider_authentication"])
if __name__=="__main__": unittest.main()
