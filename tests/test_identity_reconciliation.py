import unittest

from papi_core.identity_reconciliation import (
    IdentityReconciliationError, reconcile_identity_snapshots,
)


class IdentityReconciliationTests(unittest.TestCase):
    def test_matching_snapshots_are_consistent_and_read_only(self):
        registry = [{
            "id": "agent-a", "status": "active",
            "permissions": ["read"], "prohibited": ["spend"],
        }]
        ledger = [{
            "agent_id": "agent-a", "status": "active", "revision": 1,
            "key_version": 1, "permissions": ["read"], "prohibited": ["spend"],
        }]
        result = reconcile_identity_snapshots(registry, ledger)
        self.assertTrue(result["consistent"])
        self.assertFalse(result["fail_closed"])
        self.assertEqual(result["mode"], "read_only")
        self.assertEqual(len(result["report_sha256"]), 64)

    def test_defined_agent_must_not_appear_as_runtime_identity(self):
        result = reconcile_identity_snapshots(
            [{"id": "agent-a", "status": "planned"}],
            [{"agent_id": "agent-a", "status": "active", "revision": 1,
              "key_version": 1, "permissions": [], "prohibited": []}],
        )
        self.assertTrue(result["fail_closed"])
        self.assertEqual(result["discrepancies"][0]["code"], "UNAUTHORIZED_LEDGER_ACTIVATION")

    def test_orphan_ledger_state_is_critical(self):
        result = reconcile_identity_snapshots(
            [], [{"agent_id": "orphan", "status": "active"}],
        )
        self.assertTrue(result["fail_closed"])
        self.assertEqual(result["discrepancies"][0]["code"], "LEDGER_ORPHAN")

    def test_active_registry_without_ledger_is_critical(self):
        result = reconcile_identity_snapshots(
            [{"id": "agent-a", "status": "active"}], [],
        )
        self.assertTrue(result["fail_closed"])
        self.assertEqual(result["discrepancies"][0]["code"], "LEDGER_MISSING")

    def test_status_and_permission_drift_are_reported(self):
        result = reconcile_identity_snapshots(
            [{"id": "agent-a", "status": "active", "permissions": ["read"],
              "prohibited": ["spend"]}],
            [{"agent_id": "agent-a", "status": "revoked", "revision": 2,
              "key_version": 1, "permissions": ["write"], "prohibited": []}],
        )
        codes = {item["code"] for item in result["discrepancies"]}
        self.assertIn("STATUS_MISMATCH", codes)
        self.assertIn("PERMISSIONS_MISMATCH", codes)
        self.assertIn("PROHIBITIONS_MISMATCH", codes)
        self.assertTrue(result["fail_closed"])

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaises(IdentityReconciliationError):
            reconcile_identity_snapshots(
                [{"id": "agent-a"}, {"id": "agent-a"}], [],
            )

    def test_invalid_snapshot_shape_is_rejected(self):
        with self.assertRaises(IdentityReconciliationError):
            reconcile_identity_snapshots([{"status": "active"}], [])

    def test_report_is_deterministic(self):
        registry = [{"id": "agent-b", "status": "planned"},
                    {"id": "agent-a", "status": "planned"}]
        first = reconcile_identity_snapshots(registry, [])
        second = reconcile_identity_snapshots(list(reversed(registry)), [])
        self.assertEqual(first["report_sha256"], second["report_sha256"])


if __name__ == "__main__":
    unittest.main()
