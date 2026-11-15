import tempfile
import unittest
from pathlib import Path

from papi_core.image_asset_center import LocalImageAssetCenter
from papi_core.image_factory import plan_book_images
from papi_core.image_production_engine import ImageProductionEngine


PNG = b"\x89PNG\r\n\x1a\n" + b"papi-test-image"


class FakeGenerator:
    def __init__(self, *, fail_keys=None):
        self.calls = []
        self.fail_keys = set(fail_keys or ())

    def generate_many(self, *, jobs, now=None):
        self.calls.append(jobs)
        return [
            ({"status": "failed", "idempotency_key": job["idempotency_key"], "error": "mock failure"}
             if job["idempotency_key"] in self.fail_keys else
             {"status": "generated", "idempotency_key": job["idempotency_key"],
              "image_bytes": PNG, "content_type": "image/png"})
            for job in jobs
        ]


class ImageProductionEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = LocalImageAssetCenter(Path(self.temp.name))
        self.pages = [
            {"page_id": f"page-{i}", "page_number": i, "prompt": f"Draw page {i}"}
            for i in range(1, 4)
        ]
        self.batch = plan_book_images(
            book_id="book-113", pages=self.pages,
            model="@cf/test/image", model_costs={"@cf/test/image": 10},
        )[0]

    def test_generates_and_persists_all_missing_images(self):
        generator = FakeGenerator()
        engine = ImageProductionEngine(generator=generator, asset_center=self.store)
        report = engine.execute_batch(self.batch)
        self.assertEqual(report["stored_count"], 3)
        self.assertEqual(report["provider_submissions"], 3)
        self.assertEqual(len(self.store.list_assets(book_id="book-113")), 3)
        self.assertTrue(all(x["status"] == "pending_visual_review" for x in self.store.list_assets(book_id="book-113")))

    def test_resume_skips_existing_assets_without_provider_calls(self):
        generator = FakeGenerator()
        engine = ImageProductionEngine(generator=generator, asset_center=self.store)
        first = engine.execute_batch(self.batch)
        second = engine.execute_batch(self.batch)
        self.assertEqual(first["stored_count"], 3)
        self.assertEqual(second["skipped_existing_count"], 3)
        self.assertEqual(second["provider_submissions"], 0)
        self.assertEqual(len(generator.calls), 1)

    def test_failure_isolated_and_successful_siblings_are_saved(self):
        failed_key = self.batch.jobs[1].idempotency_key
        generator = FakeGenerator(fail_keys={failed_key})
        engine = ImageProductionEngine(generator=generator, asset_center=self.store)
        report = engine.execute_batch(self.batch)
        self.assertEqual(report["stored_count"], 2)
        self.assertEqual(report["failed_count"], 1)
        self.assertEqual(len(self.store.list_assets(book_id="book-113")), 2)

    def test_provider_result_mismatch_is_not_retried(self):
        class Mismatch:
            def generate_many(self, *, jobs, now=None):
                return [{"status": "generated", "idempotency_key": "wrong", "image_bytes": PNG}
                        for _ in jobs]
        engine = ImageProductionEngine(generator=Mismatch(), asset_center=self.store)
        report = engine.execute_batch(self.batch)
        self.assertEqual(report["uncertain_count"], 3)
        self.assertEqual(report["automatic_retries"], 0)
        self.assertEqual(self.store.list_assets(book_id="book-113"), [])


if __name__ == "__main__":
    unittest.main()
