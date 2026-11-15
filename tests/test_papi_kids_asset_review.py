import hashlib
import tempfile
import unittest
from pathlib import Path

from papi_core.image_asset_center import LocalImageAssetCenter
from papi_core.image_quality_audit import ImageQualityAuditLog
from papi_core.image_quality_review import REQUIRED_CHECKS
from papi_core.papi_kids_asset_review import review_pkp0001_assets


PNG = b"\x89PNG\r\n\x1a\n" + b"fake-png-payload"


def passing_reviewer(**kwargs):
    return {"checks": {
        name: {"score": 0.96, "passed": True, "findings": []}
        for name in REQUIRED_CHECKS
    }}


class PapiKidsAssetReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.assets = LocalImageAssetCenter(root / "assets")
        self.audit = ImageQualityAuditLog(root / "audit")
        self.asset = self.assets.put(
            book_id="PKP-0001", page_id="page-01", page_number=1,
            idempotency_key="PKP0001-page01-v1", image_bytes=PNG,
            content_type="image/png", model="@cf/test/image",
        )
        self.prompts = {"page-01": "Nia stands on a safe riverbank."}

    def test_valid_semantic_review_is_audited_but_not_human_approved(self):
        report = review_pkp0001_assets(
            asset_center=self.assets, audit_log=self.audit,
            prompts_by_page=self.prompts, reviewer=passing_reviewer)
        self.assertEqual(report["reviewed_assets"], 1)
        self.assertEqual(report["pending_human_approval"], 1)
        self.assertFalse(report["publication_authorized"])
        event = self.audit.list_events(book_id="PKP-0001", page_id="page-01")[0]
        self.assertFalse(event["human_approval_granted"])
        self.assertEqual(event["content_sha256"], hashlib.sha256(PNG).hexdigest())

    def test_missing_reviewer_stays_awaiting_visual_review(self):
        report = review_pkp0001_assets(
            asset_center=self.assets, audit_log=self.audit,
            prompts_by_page=self.prompts, reviewer=None)
        self.assertEqual(report["assets"][0]["status"], "awaiting_visual_review")
        self.assertFalse(report["assets"][0]["human_approved"])

    def test_missing_prompt_blocks_pipeline_before_audit(self):
        with self.assertRaises(ValueError):
            review_pkp0001_assets(
                asset_center=self.assets, audit_log=self.audit,
                prompts_by_page={}, reviewer=passing_reviewer)
        self.assertEqual(self.audit.list_events(book_id="PKP-0001"), [])

    def test_review_is_idempotent_for_same_asset(self):
        first = review_pkp0001_assets(
            asset_center=self.assets, audit_log=self.audit,
            prompts_by_page=self.prompts, reviewer=passing_reviewer)
        second = review_pkp0001_assets(
            asset_center=self.assets, audit_log=self.audit,
            prompts_by_page=self.prompts, reviewer=passing_reviewer)
        self.assertEqual(first["assets"][0]["audit_event_id"], second["assets"][0]["audit_event_id"])
        self.assertEqual(len(self.audit.list_events(book_id="PKP-0001")), 1)


if __name__ == "__main__":
    unittest.main()
