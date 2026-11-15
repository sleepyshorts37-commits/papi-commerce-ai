import tempfile
import unittest
from pathlib import Path

from papi_core.image_campaign import ImageCampaignError
from papi_core.image_production_engine import ImageProductionEngine
from papi_core.image_model_router import FreeImageModel
from papi_core.papi_kids_orchestrator import (
    PapiKidsOrchestrationError, prepare_pkp0001_campaign, execute_pkp0001_campaign,
)


class DummyGenerator:
    def __init__(self, models=()):
        self.models = tuple(models)
        self.calls = 0

    def generate_many(self, *, jobs, now=None):
        self.calls += 1
        return [{
            "status": "failed", "idempotency_key": job["idempotency_key"],
            "error": "mock only",
        } for job in jobs]


class DummyAssets:
    def get(self, **kwargs):
        return None

    def put(self, **kwargs):
        raise AssertionError("No successful fake generation expected")


class PapiKidsOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.prompts = root / "prompts.md"
        self.bible = root / "bible.md"
        scenes = "\n\n".join(
            f"### {i:02d} — Scene {i}\nIllustration scene {i}."
            for i in range(1, 25)
        )
        self.prompts.write_text("# Prompts\n\n" + scenes, encoding="utf-8")
        self.bible.write_text("# Character bible\nNia wears an ochre tunic.", encoding="utf-8")

    def prepare(self):
        return prepare_pkp0001_campaign(
            prompts_path=self.prompts, character_bible_path=self.bible,
            model="@cf/test/image", model_costs={"@cf/test/image": 7},
            free_quota_confirmed=True, max_batch_size=4, max_batch_units=28,
        )

    def test_creates_exactly_24_stable_page_jobs_offline(self):
        prepared = self.prepare()
        self.assertEqual(prepared["page_count"], 24)
        self.assertEqual(prepared["campaign"]["page_count"], 24)
        jobs = [job for batch in prepared["campaign"]["batches"] for job in batch.jobs]
        self.assertEqual(len(jobs), 24)
        self.assertEqual([job.page_number for job in jobs], list(range(1, 25)))
        self.assertFalse(prepared["generation_executed"])

    def test_rejects_unconfirmed_free_quota(self):
        with self.assertRaises(PapiKidsOrchestrationError):
            prepare_pkp0001_campaign(
                prompts_path=self.prompts, character_bible_path=self.bible,
                model="@cf/test/image", model_costs={"@cf/test/image": 7},
                free_quota_confirmed=False,
            )

    def test_rejects_missing_scene(self):
        self.prompts.write_text("### 01 — Only one\nOne scene", encoding="utf-8")
        with self.assertRaises(PapiKidsOrchestrationError):
            self.prepare()

    def test_execution_requires_explicit_authorization_and_zero_spend(self):
        prepared = self.prepare()
        generator = DummyGenerator([FreeImageModel("@cf/test/image", 7, True)])
        engine = ImageProductionEngine(generator=generator, asset_center=DummyAssets())
        with self.assertRaises(PapiKidsOrchestrationError):
            execute_pkp0001_campaign(prepared=prepared, engine=engine)
        with self.assertRaises(PapiKidsOrchestrationError):
            execute_pkp0001_campaign(
                prepared=prepared, engine=engine, generation_authorized=True,
                free_quota_confirmed=True, spend_limit_minor=1,
            )
        self.assertEqual(generator.calls, 0)

    def test_rejects_adapter_without_confirmed_free_model(self):
        prepared = self.prepare()
        engine = ImageProductionEngine(generator=DummyGenerator(), asset_center=DummyAssets())
        with self.assertRaises(PapiKidsOrchestrationError):
            execute_pkp0001_campaign(
                prepared=prepared, engine=engine, generation_authorized=True,
                free_quota_confirmed=True,
            )
        self.assertEqual(engine.generator.calls, 0)


if __name__ == "__main__":
    unittest.main()
