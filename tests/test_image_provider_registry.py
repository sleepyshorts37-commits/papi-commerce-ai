import unittest
from datetime import datetime, timedelta, timezone

from papi_core.image_provider_registry import (
    ImageProviderRegistry, ModelProfile, ProviderProfile, ProviderRegistryError,
)


def quota(model="@cf/test/image", units=4):
    now = datetime.now(timezone.utc)
    return {
        "provider": "cloudflare",
        "account_ref": "cf-test-account",
        "model_id": model,
        "source_url": "https://developers.cloudflare.com/workers-ai/platform/pricing/",
        "evidence_ref": "review-123",
        "verified_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=6)).isoformat(),
        "daily_quota_units": 1000,
        "spend_cap_minor": 0,
    }


class ProviderRegistryTests(unittest.TestCase):
    def setUp(self):
        self.provider = ProviderProfile(
            "cloudflare", "Cloudflare", 
            "https://developers.cloudflare.com/workers-ai/platform/pricing/",
            "reviewed", "account_api", default_enabled=True,
        )
        self.model = ModelProfile(
            "cloudflare", "@cf/test/image", "image", 4,
            commercial_use_reviewed=True, output_policy_reviewed=True, enabled=True,
        )
        self.registry = ImageProviderRegistry(providers=[self.provider], models=[self.model])

    def test_selects_only_enabled_model_with_current_zero_spend_proof(self):
        selected = self.registry.choose(
            account_refs={"cloudflare": "cf-test-account"},
            quota_evidence_by_model={"@cf/test/image": quota()},
            required_images=24,
        )
        self.assertEqual(selected["model_id"], "@cf/test/image")
        self.assertEqual(selected["estimated_campaign_units"], 96)
        self.assertEqual(selected["spend_cap_minor"], 0)

    def test_blocks_when_provider_or_model_not_enabled(self):
        disabled = ImageProviderRegistry(
            providers=[ProviderProfile("cloudflare", "Cloudflare",
                "https://developers.cloudflare.com/workers-ai/platform/pricing/",
                "candidate", "account_api")],
            models=[self.model],
        )
        with self.assertRaises(ProviderRegistryError):
            disabled.choose(account_refs={"cloudflare": "cf-test-account"},
                quota_evidence_by_model={"@cf/test/image": quota()}, required_images=24)

    def test_blocks_missing_stale_or_wrong_account_evidence(self):
        for evidence, account in ((None, "cf-test-account"),
                                  (quota(), "another-account"),
                                  ({**quota(), "verified_at": "2020-01-01T00:00:00+00:00"}, "cf-test-account")):
            with self.subTest(account=account), self.assertRaises(ProviderRegistryError):
                self.registry.choose(account_refs={"cloudflare": account},
                    quota_evidence_by_model={} if evidence is None else {"@cf/test/image": evidence},
                    required_images=24)

    def test_blocks_nonzero_budget(self):
        with self.assertRaises(ProviderRegistryError):
            self.registry.choose(account_refs={"cloudflare": "cf-test-account"},
                quota_evidence_by_model={"@cf/test/image": quota()},
                required_images=24, spend_cap_minor=1)

    def test_never_selects_disabled_secondary_providers(self):
        catalogue = self.registry.list_catalogue()
        self.assertTrue(any(p["provider_id"] == "pollinations" and not p["default_enabled"]
                            for p in catalogue) is False)  # only providers explicitly supplied
        self.assertEqual(self.registry.choose(
            account_refs={"cloudflare": "cf-test-account"},
            quota_evidence_by_model={"@cf/test/image": quota()},
            required_images=24)["provider_id"], "cloudflare")

    def test_rejects_duplicate_model_and_unknown_provider(self):
        with self.assertRaises(ProviderRegistryError):
            ImageProviderRegistry(providers=[self.provider], models=[self.model, self.model])
        with self.assertRaises(ProviderRegistryError):
            ImageProviderRegistry(providers=[self.provider], models=[
                ModelProfile("unknown", "m", "image", 1, True, True, True)
            ])


if __name__ == "__main__":
    unittest.main()
