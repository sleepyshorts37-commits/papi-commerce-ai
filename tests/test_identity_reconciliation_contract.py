import copy
import hashlib
import json
import unittest

from papi_core.identity_reconciliation import reconcile_identity_snapshots
from papi_core.identity_reconciliation_contract import (
    IdentityReconciliationReportContractError,
    validate_reconciliation_report,
)


class IdentityReconciliationReportContractTests(unittest.TestCase):
    def valid_report(self):
        return reconcile_identity_snapshots(
            [{"id": "agent-a", "status": "active", "permissions": ["read"],
              "prohibited": ["spend"]}],
            [{"agent_id": "agent-a", "status": "active", "revision": 1,
              "key_version": 1, "permissions": ["read"], "prohibited": ["spend"]}],
        )

    def test_accepts_valid_report(self):
        validate_reconciliation_report(self.valid_report())

    def test_rejects_tampered_digest(self):
        report = self.valid_report()
        report["registry_count"] = 4
        with self.assertRaises(IdentityReconciliationReportContractError):
            validate_reconciliation_report(report)

    def test_rejects_inconsistent_derived_count(self):
        report = self.valid_report()
        report["discrepancy_count"] = 1
        with self.assertRaises(IdentityReconciliationReportContractError):
            validate_reconciliation_report(report)

    def test_rejects_non_boolean_flag(self):
        report = self.valid_report()
        report["consistent"] = 1
        with self.assertRaises(IdentityReconciliationReportContractError):
            validate_reconciliation_report(report)

    def test_rejects_duplicate_identity_code(self):
        report = self.valid_report()
        item = {
            "agent_id": "agent-a", "code": "DRIFT", "severity": "high",
            "registry_status": "active", "ledger_status": "active",
            "message": "Écart.",
        }
        report["discrepancies"] = [item, copy.deepcopy(item)]
        report["discrepancy_count"] = 2
        report["high_count"] = 2
        report["consistent"] = False
        report["report_sha256"] = hashlib.sha256(json.dumps(
            {key: value for key, value in report.items() if key != "report_sha256"},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode("utf-8")).hexdigest()
        with self.assertRaises(IdentityReconciliationReportContractError):
            validate_reconciliation_report(report)

    def test_rejects_invalid_severity(self):
        report = self.valid_report()
        report["discrepancies"] = [{
            "agent_id": "agent-a", "code": "DRIFT", "severity": "low",
            "registry_status": "active", "ledger_status": "active",
            "message": "Écart.",
        }]
        with self.assertRaises(IdentityReconciliationReportContractError):
            validate_reconciliation_report(report)

    def test_rejects_wrong_digest_format(self):
        report = self.valid_report()
        report["report_sha256"] = "not-a-digest"
        with self.assertRaises(IdentityReconciliationReportContractError):
            validate_reconciliation_report(report)

    def test_rejects_missing_schema_field(self):
        report = self.valid_report()
        del report["mode"]
        with self.assertRaises(IdentityReconciliationReportContractError):
            validate_reconciliation_report(report)


if __name__ == "__main__":
    unittest.main()
