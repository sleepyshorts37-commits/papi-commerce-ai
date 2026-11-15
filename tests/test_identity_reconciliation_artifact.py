import copy
import json
import unittest

from papi_core.identity_reconciliation import reconcile_identity_snapshots
from papi_core.identity_reconciliation_artifact import (
    MAX_RECONCILIATION_REPORT_BYTES,
    IdentityReconciliationArtifactError,
    canonicalize_reconciliation_report,
    load_reconciliation_report,
)


class IdentityReconciliationArtifactTests(unittest.TestCase):
    def valid_report(self):
        return reconcile_identity_snapshots(
            [{"id": "agent-a", "status": "active", "permissions": ["read"],
              "prohibited": ["spend"]}],
            [{"agent_id": "agent-a", "status": "active", "revision": 1,
              "key_version": 1, "permissions": ["read"], "prohibited": ["spend"]}],
        )

    def test_loads_valid_serialized_report(self):
        report = self.valid_report()
        raw = json.dumps(report, ensure_ascii=False).encode("utf-8")
        self.assertEqual(load_reconciliation_report(raw), report)

    def test_canonicalization_is_stable_and_does_not_mutate(self):
        report = self.valid_report()
        before = copy.deepcopy(report)
        first = canonicalize_reconciliation_report(report)
        second = canonicalize_reconciliation_report(report)
        self.assertEqual(first, second)
        self.assertEqual(report, before)
        self.assertEqual(load_reconciliation_report(first), report)

    def test_rejects_non_bytes_input(self):
        with self.assertRaises(IdentityReconciliationArtifactError):
            load_reconciliation_report("{}")

    def test_rejects_oversized_document_before_parsing(self):
        raw = b" " * (MAX_RECONCILIATION_REPORT_BYTES + 1)
        with self.assertRaises(IdentityReconciliationArtifactError):
            load_reconciliation_report(raw)

    def test_rejects_invalid_utf8(self):
        with self.assertRaises(IdentityReconciliationArtifactError):
            load_reconciliation_report(b"\\xff")

    def test_rejects_duplicate_keys(self):
        with self.assertRaises(IdentityReconciliationArtifactError):
            load_reconciliation_report(b'{"outer":{"x":1,"x":2}}')

    def test_rejects_non_standard_numeric_constants(self):
        with self.assertRaises(IdentityReconciliationArtifactError):
            load_reconciliation_report(b'{"value":NaN}')

    def test_rejects_non_object_root(self):
        with self.assertRaises(IdentityReconciliationArtifactError):
            load_reconciliation_report(b"[]")

    def test_normalizes_python_json_integer_digit_limit(self):
        # Python's JSON decoder raises ValueError for integer strings beyond
        # its configured digit limit; callers must still receive the stable
        # artifact-boundary exception.
        raw = b'{"unexpected":' + (b"9" * 5000) + b"}"
        with self.assertRaises(IdentityReconciliationArtifactError):
            load_reconciliation_report(raw)

    def test_rejects_excessive_json_nesting_with_stable_error(self):
        # The document is well below the byte limit but exceeds the parser's
        # recursion capacity. The public boundary must normalize that failure.
        raw = (b"[" * 2000) + b"0" + (b"]" * 2000)
        self.assertLess(len(raw), MAX_RECONCILIATION_REPORT_BYTES)
        with self.assertRaises(IdentityReconciliationArtifactError):
            load_reconciliation_report(raw)

    def test_rejects_invalid_contract_after_parsing(self):
        report = self.valid_report()
        report["report_sha256"] = "0" * 64
        raw = json.dumps(report).encode("utf-8")
        with self.assertRaises(IdentityReconciliationArtifactError):
            load_reconciliation_report(raw)

    def test_rejects_invalid_report_during_canonicalization(self):
        report = self.valid_report()
        report["consistent"] = 1
        with self.assertRaises(IdentityReconciliationArtifactError):
            canonicalize_reconciliation_report(report)


if __name__ == "__main__":
    unittest.main()
