import json
import tempfile
import unittest
from pathlib import Path
from papi_core.finance import FinanceError, append_entry, finance_report, load_ledger, validate_entry, validate_ledger

def ledger():
    return {"project":"PAPI COMMERCE AI","currency":"XOF","entries":[],"policy":"No unverified revenue."}

def income(**changes):
    row={"id":"income-001","kind":"income","status":"verified","amount_xof":15000,
         "occurred_at":"2026-11-11T10:00:00Z","description":"Prestation exemple",
         "reference":"internal-receipt-001",
         "verification":{"method":"provider_statement","evidence_reference":"statement-line-001",
                         "verified_by":"owner","verified_at":"2026-11-11T11:00:00Z"}}
    row.update(changes); return row

class FinanceTests(unittest.TestCase):
    def test_verified_income_requires_independent_evidence(self):
        row=income(verification={"method":"manual"})
        self.assertTrue(validate_entry(row))
    def test_expense_requires_approval_before_approved_or_paid(self):
        row={"id":"expense-001","kind":"expense","status":"paid","amount_xof":5000,
             "occurred_at":"2026-11-11T10:00:00Z","description":"Frais test","reference":"expense-ref-001",
             "payment_evidence":"receipt-001"}
        self.assertTrue(any("approbation" in e for e in validate_entry(row)))
    def test_sensitive_fields_rejected(self):
        row=income(); row["provider_account_number"]="123"
        self.assertTrue(any("sensible" in e for e in validate_entry(row)))
    def test_refund_must_reference_existing_entry(self):
        row={"id":"refund-001","kind":"refund","status":"pending_verification","amount_xof":1000,
             "occurred_at":"2026-11-11T10:00:00Z","description":"Remboursement","reference":"refund-ref-001",
             "related_entry_id":"income-missing"}
        self.assertTrue(any("origine inconnue" in e for e in validate_ledger({**ledger(),"entries":[row]})))
    def test_append_is_idempotent_and_append_only(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"ledger.json"
            path.write_text(json.dumps(ledger()),encoding="utf-8")
            row=income()
            self.assertTrue(append_entry(row,path))
            self.assertFalse(append_entry(row,path))
            self.assertEqual(len(load_ledger(path)["entries"]),1)
    def test_report_counts_only_verified_and_paid_entries(self):
        data=ledger(); data["entries"]=[income(),
          {"id":"income-002","kind":"income","status":"pending_verification","amount_xof":9000,
           "occurred_at":"2026-11-11T10:00:00Z","description":"En attente","reference":"pending-ref-002"},
          {"id":"expense-001","kind":"expense","status":"paid","amount_xof":2000,
           "occurred_at":"2026-11-11T10:00:00Z","description":"Dépense test","reference":"expense-ref-001",
           "approval":{"approved_by":"owner","approval_reference":"approval-001","approved_at":"2026-11-11T09:00:00Z"},
           "payment_evidence":"receipt-001"}]
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"ledger.json"; path.write_text(json.dumps(data),encoding="utf-8")
            report=finance_report(path)
        self.assertEqual(report["verified_income_xof"],15000)
        self.assertEqual(report["pending_verification_xof"],9000)
        self.assertEqual(report["net_verified_cashflow_xof"],13000)
        self.assertFalse(report["autonomous_payments_enabled"])
    def test_duplicate_payment_evidence_is_rejected(self):
        a=income(); b=income(id="income-002",reference="internal-receipt-002")
        self.assertTrue(validate_ledger({**ledger(),"entries":[a,b]}))
    def test_corrupt_ledger_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"ledger.json"; path.write_text("{broken",encoding="utf-8")
            with self.assertRaises(FinanceError): load_ledger(path)

if __name__=="__main__": unittest.main()
