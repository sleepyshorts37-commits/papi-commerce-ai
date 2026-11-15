import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from papi_core.image_provider_registry import (
    ImageProviderRegistry, ModelProfile, ProviderProfile, ProviderRegistryError,
)
from papi_core.papi_kids_orchestrator import (
    PapiKidsOrchestrationError, prepare_pkp0001_campaign_from_registry,
)


def proof():
    now = datetime.now(timezone.utc)
    return {
        "provider": "cloudflare", "account_ref": "cf-account-001",
        "model_id": "@cf/test/image",
        "source_url": "https://developers.cloudflare.com/workers-ai/platform/pricing/",
        "evidence_ref": "review-122",
        "verified_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=6)).isoformat(),
        "daily_quota_units": 1000, "spend_cap_minor": 0,
    }


class RegistryOrchestratorIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.prompts = root / "prompts.md"
        self.bible = root / "bible.md"
        self.prompts.write_text(
            "# prompts\n\n" + "\n\n".join(
                f"### {i:02d} — Scene {i}\nA safe original children's illustration."
                for i in range(1, 25)
            ), encoding="utf-8")
        self.bible.write_text("# Bible\nNia wears an ochre tunic.", encoding="utf-8")
        provider = ProviderProfile(
            "cloudflare", "Cloudflare",
            "https://developers.cloudflare.com/workers-ai/platform/pricing/",
            "operator_reviewed", "account_api", default_enabled=True)
        model = ModelProfile(
            "cloudflare", "@cf/test/image", "image", 4,
            commercial_use_reviewed=True, output_policy_reviewed=True, enabled=True)
        self.registry = ImageProviderRegistry(providers=[provider], models=[model])

    def test_registry_selects_model_and_prepares_all_24_scenes(self):
        prepared = prepare_pkp0001_campaign_from_registry(
            registry=self.registry,
            prompts_path=self.prompts, character_bible_path=self.bible,
            account_refs={"cloudflare": "cf-account-001"},
            quota_evidence_by_model={"@cf/test/image": proof()},
            max_batch_size=4, max_batch_units=16,
        )
        self.assertEqual(prepared["provider_selection"]["provider_id"], "cloudflare")
        self.assertEqual(prepared["model"], "@cf/test/image")
        self.assertEqual(prepared["page_count"], 24)
        self.assertFalse(prepared["generation_executed"])

    def test_registry_empty_or_ineligible_blocks_planning(self):
        empty = ImageProviderRegistry(providers=[
            ProviderProfile("cloudflare", "Cloudflare",
                "https://developers.cloudflare.com/workers-ai/platform/pricing/",
                "candidate", "account_api")], models=[])
        with self.assertRaises(PapiKidsOrchestrationError):
            prepare_pkp0001_campaign_from_registry(
                registry=empty, prompts_path=self.prompts,
                character_bible_path=self.bible, account_refs={},
                quota_evidence_by_model={})

    def test_registry_cannot_select_paid_or_unreviewed_model(self):
        provider = ProviderProfile(
            "cloudflare", "Cloudflare",
            "https://developers.cloudflare.com/workers-ai/platform/pricing/",
            "candidate", "account_api", default_enabled=True)
        model = ModelProfile("cloudflare", "@cf/test/image", "image", 4,
            commercial_use_reviewed=False, output_policy_reviewed=True, enabled=True)
        registry = ImageProviderRegistry(providers=[provider], models=[model])
        with self.assertRaises(PapiKidsOrchestrationError):
            prepare_pkp0001_campaign_from_registry(
                registry=registry, prompts_path=self.prompts,
                character_bible_path=self.bible,
                account_refs={"cloudflare": "cf-account-001"},
                quota_evidence_by_model={"@cf/test/image": proof()})


if __name__ == "__main__":
    unittest.main()
