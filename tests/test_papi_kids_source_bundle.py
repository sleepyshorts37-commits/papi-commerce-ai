import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from papi_core.image_provider_registry import (
    ImageProviderRegistry, ModelProfile, ProviderProfile,
)
from papi_core.papi_kids_orchestrator import (
    PapiKidsOrchestrationError, prepare_pkp0001_from_project_sources,
)


def proof():
    now = datetime.now(timezone.utc)
    return {
        "provider": "cloudflare", "account_ref": "cf-account-001",
        "model_id": "@cf/test/image",
        "source_url": "https://developers.cloudflare.com/workers-ai/platform/pricing/",
        "evidence_ref": "review-125",
        "verified_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=6)).isoformat(),
        "daily_quota_units": 1000, "spend_cap_minor": 0,
    }


class PKP0001SourceBundleTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        provider = ProviderProfile(
            "cloudflare", "Cloudflare",
            "https://developers.cloudflare.com/workers-ai/platform/pricing/",
            "reviewed", "account_api", default_enabled=True)
        model = ModelProfile(
            "cloudflare", "@cf/test/image", "image", 4,
            commercial_use_reviewed=True, output_policy_reviewed=True, enabled=True)
        self.registry = ImageProviderRegistry(providers=[provider], models=[model])

    def test_loads_and_validates_committed_24_page_source_bundle(self):
        prepared = prepare_pkp0001_from_project_sources(
            project_root=self.root, registry=self.registry,
            account_refs={"cloudflare": "cf-account-001"},
            quota_evidence_by_model={"@cf/test/image": proof()},
        )
        self.assertEqual(prepared["page_count"], 24)
        self.assertEqual(prepared["source_bundle"]["manuscript_pages"], 24)
        self.assertEqual(prepared["source_bundle"]["storyboard_pages"], 24)
        self.assertEqual(prepared["source_bundle"]["source_status"],
                         "editorial_v2_not_human_approved")
        self.assertTrue(prepared["human_editorial_approval_required"])

    def test_missing_project_source_fails_closed(self):
        with self.assertRaises(PapiKidsOrchestrationError):
            prepare_pkp0001_from_project_sources(
                project_root=self.root / "missing", registry=self.registry,
                account_refs={"cloudflare": "cf-account-001"},
                quota_evidence_by_model={"@cf/test/image": proof()},
            )


if __name__ == "__main__":
    unittest.main()
