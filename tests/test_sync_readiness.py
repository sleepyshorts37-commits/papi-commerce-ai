import unittest

from papi_core.reconciliation import build_reconciliation_preview
from papi_core.principal import _issue_authenticated_agent_principal
from papi_core.sync_readiness import SyncReadinessError, build_sync_readiness_report


class SyncReadinessTests(unittest.TestCase):
    def setUp(self):
        self.principal = _issue_authenticated_agent_principal("astou")
        self.preview = build_reconciliation_preview(
            principal=self.principal, local_memory=[], remote_memory=[],
            local_messages=[], remote_messages=[],
        )

    def test_valid_preview_is_ready_only_for_preview(self):
        report = build_sync_readiness_report(self.preview)
        self.assertEqual(report["status"], "preview_ready")
        self.assertFalse(report["sync_enabled"])
        self.assertFalse(report["writes_performed"])
        self.assertTrue(report["blockers"])

    def test_non_preview_or_write_capable_payload_is_rejected(self):
        for change in ({"mode": "sync"}, {"writes_performed": True}):
            payload = {**self.preview, **change}
            with self.assertRaises(SyncReadinessError):
                build_sync_readiness_report(payload)

    def test_counts_must_match_buckets(self):
        payload = {**self.preview, "counts": {**self.preview["counts"], "identical": 1}}
        with self.assertRaises(SyncReadinessError):
            build_sync_readiness_report(payload)

    def test_missing_or_malformed_sections_are_rejected(self):
        payload = {**self.preview, "messages": {}}
        with self.assertRaises(SyncReadinessError):
            build_sync_readiness_report(payload)

    def test_differences_are_explicit_blockers_for_human_review(self):
        preview = build_reconciliation_preview(
            principal=self.principal,
            local_memory=[{"memory_id":"M-1","scope":"shared","sensitivity":"normal",
                           "event_type":"remember","category":"fact","title":"T",
                           "content":"C","confidence":1,"tags":[]}],
            remote_memory=[], local_messages=[], remote_messages=[],
        )
        report = build_sync_readiness_report(preview)
        self.assertTrue(report["requires_human_review"])
        self.assertIn("Des différences nécessitent une revue humaine avant toute décision.",
                      report["blockers"])


if __name__ == "__main__":
    unittest.main()
