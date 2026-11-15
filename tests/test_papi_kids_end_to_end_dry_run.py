import hashlib
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from papi_core.image_asset_center import LocalImageAssetCenter
from papi_core.image_model_router import FreeImageModel, FreeImageModelRouter
from papi_core.image_production_engine import ImageProductionEngine
from papi_core.image_provider_cloudflare import InMemoryNeuronQuotaLedger
from papi_core.image_provider_registry import ImageProviderRegistry, ModelProfile, ProviderProfile
from papi_core.image_quality_audit import ImageQualityAuditLog
from papi_core.image_quality_review import REQUIRED_CHECKS
from papi_core.papi_kids_asset_review import review_pkp0001_assets
from papi_core.papi_kids_orchestrator import (
    prepare_pkp0001_from_project_sources, execute_pkp0001_campaign,
)


PNG = b"\x89PNG\r\n\x1a\nPAPI-KIDS-TEST-ONLY"


def evidence():
    now = datetime.now(timezone.utc)
    return {
        "provider": "cloudflare", "account_ref": "cf-test-account",
        "model_id": "@cf/test/image",
        "source_url": "https://developers.cloudflare.com/workers-ai/platform/pricing/",
        "evidence_ref": "test-attestation-129",
        "verified_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=12)).isoformat(),
        "daily_quota_units": 1000, "spend_cap_minor": 0,
    }


class FakeProvider:
    def __init__(self):
        self.account_id = "cf-test-account"
        self.model_costs = {"@cf/test/image": 4}
        self.ledger = InMemoryNeuronQuotaLedger(daily_limit=1000)
        self.calls = 0

    def generate_many(self, *, jobs, now=None):
        results = []
        for job in jobs:
            reservation = self.ledger.reserve(
                idempotency_key=job["idempotency_key"],
                estimated_neurons=4, now=now, model=job["model"])
            self.ledger.commit(reservation, actual_neurons=4)
            self.calls += 1
            results.append({
                "status": "generated",
                "idempotency_key": job["idempotency_key"],
                "image_bytes": PNG,
                "content_type": "image/png",
            })
        return results


def passing_reviewer(**kwargs):
    return {"checks": {
        name: {"score": 0.97, "passed": True, "findings": []}
        for name in REQUIRED_CHECKS
    }}


class PKP0001DryRunEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.provider = ProviderProfile(
            "cloudflare", "Cloudflare",
            "https://developers.cloudflare.com/workers-ai/platform/pricing/",
            "test-only", "account_api", default_enabled=True)
        self.model = ModelProfile(
            "cloudflare", "@cf/test/image", "image", 4,
            commercial_use_reviewed=True, output_policy_reviewed=True, enabled=True)
        self.registry = ImageProviderRegistry(
            providers=[self.provider], models=[self.model])

    def test_full_24_page_dry_run_plans_generates_stores_reviews_and_audits(self):
        prepared = prepare_pkp0001_from_project_sources(
            project_root=self.root, registry=self.registry,
            account_refs={"cloudflare": "cf-test-account"},
            quota_evidence_by_model={"@cf/test/image": evidence()},
        )
        generator = FreeImageModelRouter(
            provider=self.provider_adapter(),
            models=[FreeImageModel("@cf/test/image", 4, True)],
            max_batch_size=24,
        )
        assets = LocalImageAssetCenter(Path(self.temp.name) / "assets")
        engine = ImageProductionEngine(generator=generator, asset_center=assets)
        execution = execute_pkp0001_campaign(
            prepared=prepared, engine=engine,
            quota_evidence=evidence(), generation_authorized=True,
            spend_limit_minor=0, max_batches_per_run=6,
        )
        self.assertEqual(execution["execution"]["page_count"], 24)
        self.assertEqual(execution["execution"]["complete"], True)
        self.assertEqual(execution["execution"]["batch_reports"][0]["stored_count"], 4)
        self.assertEqual(self.provider_adapter_instance.calls, 24)
        stored = assets.list_assets(book_id="PKP-0001", status="pending_visual_review")
        self.assertEqual(len(stored), 24)

        audit = ImageQualityAuditLog(Path(self.temp.name) / "audit")
        prompts = {f"page-{i:02d}": f"Safe original illustration page {i}."
                   for i in range(1, 25)}
        qa = review_pkp0001_assets(
            asset_center=assets, audit_log=audit,
            prompts_by_page=prompts, reviewer=passing_reviewer)
        self.assertEqual(qa["reviewed_assets"], 24)
        self.assertEqual(qa["pending_human_approval"], 24)
        self.assertFalse(qa["publication_authorized"])
        self.assertEqual(len(audit.list_events(book_id="PKP-0001")), 24)
        self.assertTrue(all(not item["human_approved"] for item in qa["assets"]))

    @property
    def provider_adapter_instance(self):
        return self._provider_adapter

    def provider_adapter(self):
        self._provider_adapter = FakeProvider()
        return self._provider_adapter


if __name__ == "__main__":
    unittest.main()
