import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from papi_core.image_production_engine import ImageProductionEngine
from papi_core.image_model_router import FreeImageModel
from papi_core.image_quota_evidence import QuotaEvidenceError, validate_quota_evidence
from papi_core.papi_kids_orchestrator import (
    PapiKidsOrchestrationError, prepare_pkp0001_campaign, execute_pkp0001_campaign,
)


def evidence(*, now=None, **overrides):
    current = now or datetime.now(timezone.utc)
    result = {
        "provider": "cloudflare",
        "account_ref": "cf-account-001",
        "model_id": "@cf/test/image",
        "source_url": "https://developers.cloudflare.com/workers-ai/",
        "evidence_ref": "manual-review-2026-11",
        "verified_at": current.isoformat(),
        "expires_at": (current + timedelta(hours=12)).isoformat(),
        "daily_quota_units": 200,
        "spend_cap_minor": 0,
    }
    result.update(overrides)
    return result


class DummyGenerator:
    def __init__(self, models=()):
        self.models = tuple(models)
        self.calls = 0
        self.provider = None

    def generate_many(self, *, jobs, now=None):
        self.calls += 1
        return [{"status": "failed", "idempotency_key": job["idempotency_key"],
                 "error": "mock only"} for job in jobs]


class DummyAssets:
    def get(self, **kwargs):
        return None

    def put(self, **kwargs):
        raise AssertionError("No successful fake generation expected")


class QuotaEvidenceTests(unittest.TestCase):
    def test_rejects_missing_or_expired_evidence(self):
        now = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
        with self.assertRaises(QuotaEvidenceError):
            validate_quota_evidence({}, provider="cloudflare", account_ref="cf-account-001",
                model_id="@cf/test/image", estimated_units_per_image=7, required_images=24, now=now)
        stale = evidence(now=now - timedelta(days=2))
        with self.assertRaisesRegex(QuotaEvidenceError, "24 h"):
            validate_quota_evidence(stale, provider="cloudflare", account_ref="cf-account-001",
                model_id="@cf/test/image", estimated_units_per_image=7, required_images=24, now=now)

    def test_rejects_account_model_or_daily_quota_mismatch(self):
        now = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
        for patch in ({"account_ref": "another-account"}, {"model_id": "@cf/other"},
                      {"daily_quota_units": 199}):
            with self.subTest(patch=patch), self.assertRaises(QuotaEvidenceError):
                validate_quota_evidence(evidence(now=now, **patch), provider="cloudflare",
                    account_ref="cf-account-001", model_id="@cf/test/image",
                    estimated_units_per_image=7, required_images=24, now=now,
                    provider_daily_limit=200, provider_model_cost=7)

    def test_rejects_campaign_larger_than_quota_and_nonzero_spend(self):
        now = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
        with self.assertRaisesRegex(QuotaEvidenceError, "supérieure"):
            validate_quota_evidence(evidence(now=now, daily_quota_units=100),
                provider="cloudflare", account_ref="cf-account-001",
                model_id="@cf/test/image", estimated_units_per_image=7,
                required_images=24, now=now)
        with self.assertRaisesRegex(QuotaEvidenceError, "non nul"):
            validate_quota_evidence(evidence(now=now, spend_cap_minor=1),
                provider="cloudflare", account_ref="cf-account-001",
                model_id="@cf/test/image", estimated_units_per_image=7,
                required_images=24, now=now)


class PapiKidsOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.prompts = root / "prompts.md"
        self.bible = root / "bible.md"
        scenes = "\\n\\n".join(
            f"### {i:02d} — Scene {i}\\nIllustration scene {i}."
            for i in range(1, 25)
        )
        self.prompts.write_text("# Prompts\\n\\n" + scenes, encoding="utf-8")
        self.bible.write_text("# Character bible\\nNia wears an ochre tunic.", encoding="utf-8")

    def prepare(self, quota=None):
        return prepare_pkp0001_campaign(
            prompts_path=self.prompts, character_bible_path=self.bible,
            model="@cf/test/image", model_costs={"@cf/test/image": 7},
            account_ref="cf-account-001", quota_evidence=quota or evidence(),
            max_batch_size=4, max_batch_units=28,
        )

    def test_creates_exactly_24_stable_page_jobs_offline(self):
        prepared = self.prepare()
        self.assertEqual(prepared["page_count"], 24)
        self.assertEqual(prepared["campaign"]["page_count"], 24)
        jobs = [job for batch in prepared["campaign"]["batches"] for job in batch.jobs]
        self.assertEqual(len(jobs), 24)
        self.assertEqual([job.page_number for job in jobs], list(range(1, 25)))
        self.assertFalse(prepared["generation_executed"])

    def test_requires_attestation_for_planning(self):
        with self.assertRaises(PapiKidsOrchestrationError):
            self.prepare({})

    def test_rejects_missing_scene(self):
        self.prompts.write_text("### 01 — Only one\\nOne scene", encoding="utf-8")
        with self.assertRaises(PapiKidsOrchestrationError):
            self.prepare()

    def test_execution_requires_explicit_authorization_and_zero_spend(self):
        prepared = self.prepare()
        generator = DummyGenerator([FreeImageModel("@cf/test/image", 7, True)])
        engine = ImageProductionEngine(generator=generator, asset_center=DummyAssets())
        with self.assertRaises(PapiKidsOrchestrationError):
            execute_pkp0001_campaign(prepared=prepared, engine=engine)
        with self.assertRaises(PapiKidsOrchestrationError):
            execute_pkp0001_campaign(prepared=prepared, engine=engine,
                generation_authorized=True, spend_limit_minor=1)
        self.assertEqual(generator.calls, 0)

    def test_execution_fails_closed_without_real_provider_ledger(self):
        prepared = self.prepare()
        generator = DummyGenerator([FreeImageModel("@cf/test/image", 7, True)])
        engine = ImageProductionEngine(generator=generator, asset_center=DummyAssets())
        with self.assertRaisesRegex(PapiKidsOrchestrationError, "ledger transactionnel"):
            execute_pkp0001_campaign(prepared=prepared, engine=engine,
                quota_evidence=evidence(), generation_authorized=True)
        self.assertEqual(generator.calls, 0)


if __name__ == "__main__":
    unittest.main()
