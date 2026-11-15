import hashlib
import unittest

from papi_core.image_factory import (
    ImageFactoryError, build_asset_manifest, execute_image_batch, plan_book_images,
)


class FakeImageAdapter:
    def __init__(self, results=None):
        self.results = results
        self.calls = []

    def generate_many(self, *, jobs, now=None):
        self.calls.append((jobs, now))
        if self.results is not None:
            return self.results
        return [
            {"status": "generated", "image_bytes": b"png-" + job["idempotency_key"].encode(),
             "mime_type": "image/png"}
            for job in jobs
        ]


class ImageFactoryPlannerTests(unittest.TestCase):
    def setUp(self):
        self.pages = [
            {"page_id": f"page-{i:02d}", "page_number": i,
             "prompt": f"Illustration for page {i}", "priority": "normal"}
            for i in range(1, 6)
        ]
        self.costs = {"@cf/test/image": 100}

    def test_plans_deterministic_batches_under_count_and_quota_caps(self):
        first = plan_book_images(book_id="book-001", pages=self.pages,
                                 model="@cf/test/image", model_costs=self.costs,
                                 max_batch_size=2, max_batch_units=200)
        second = plan_book_images(book_id="book-001", pages=self.pages,
                                  model="@cf/test/image", model_costs=self.costs,
                                  max_batch_size=2, max_batch_units=200)
        self.assertEqual(first, second)
        self.assertEqual([len(batch.jobs) for batch in first], [2, 2, 1])
        self.assertTrue(all(batch.estimated_units <= 200 for batch in first))
        self.assertEqual([job.page_number for b in first for job in b.jobs], [1, 2, 3, 4, 5])

    def test_priority_orders_work_without_losing_page_numbers(self):
        pages = [
            {**self.pages[0], "priority": "low"},
            {**self.pages[1], "priority": "urgent"},
            {**self.pages[2], "priority": "high"},
        ]
        batches = plan_book_images(book_id="book-001", pages=pages,
                                   model="@cf/test/image", model_costs=self.costs)
        self.assertEqual([job.page_number for b in batches for job in b.jobs], [2, 3, 1])

    def test_idempotency_key_is_stable_and_within_shared_quota_limit(self):
        batches = plan_book_images(book_id="book-001", pages=self.pages[:1],
                                   model="@cf/test/image", model_costs=self.costs)
        key = batches[0].jobs[0].idempotency_key
        self.assertTrue(key.startswith("papi-image:"))
        self.assertLessEqual(len(key), 180)
        self.assertEqual(key, plan_book_images(
            book_id="book-001", pages=self.pages[:1], model="@cf/test/image",
            model_costs=self.costs)[0].jobs[0].idempotency_key)

    def test_rejects_unknown_model_duplicate_pages_and_invalid_budget(self):
        with self.assertRaises(ImageFactoryError):
            plan_book_images(book_id="book-001", pages=self.pages,
                             model="@cf/unknown", model_costs=self.costs)
        duplicate = [self.pages[0], {**self.pages[1], "page_id": self.pages[0]["page_id"]}]
        with self.assertRaises(ImageFactoryError):
            plan_book_images(book_id="book-001", pages=duplicate,
                             model="@cf/test/image", model_costs=self.costs)
        with self.assertRaises(ImageFactoryError):
            plan_book_images(book_id="book-001", pages=self.pages,
                             model="@cf/test/image", model_costs=self.costs,
                             max_batch_units=99)

    def test_execute_submits_only_explicit_batch_and_manifest_hashes_assets(self):
        batch = plan_book_images(book_id="book-001", pages=self.pages[:2],
                                 model="@cf/test/image", model_costs=self.costs)[0]
        adapter = FakeImageAdapter()
        results = execute_image_batch(adapter, batch)
        manifest = build_asset_manifest(book_id="book-001", batch=batch, results=results)
        self.assertEqual(len(adapter.calls), 1)
        self.assertEqual(manifest["generated_count"], 2)
        self.assertEqual(manifest["failed_count"], 0)
        asset = manifest["assets"][0]
        expected = hashlib.sha256(results[0]["image_bytes"]).hexdigest()
        self.assertEqual(asset["content_sha256"], expected)
        self.assertFalse(asset["human_approved"])
        self.assertNotIn("image_bytes", asset)

    def test_manifest_keeps_failed_items_without_auto_retry(self):
        batch = plan_book_images(book_id="book-001", pages=self.pages[:1],
                                 model="@cf/test/image", model_costs=self.costs)[0]
        adapter = FakeImageAdapter([{"status": "failed", "error": "timeout"}])
        results = execute_image_batch(adapter, batch)
        manifest = build_asset_manifest(book_id="book-001", batch=batch, results=results)
        self.assertEqual(adapter.calls.__len__(), 1)
        self.assertEqual(manifest["failed_count"], 1)
        self.assertEqual(manifest["assets"][0]["status"], "generation_failed")

    def test_rejects_mismatched_results_and_missing_image_bytes(self):
        batch = plan_book_images(book_id="book-001", pages=self.pages[:1],
                                 model="@cf/test/image", model_costs=self.costs)[0]
        with self.assertRaises(ImageFactoryError):
            build_asset_manifest(book_id="another-book", batch=batch,
                                 results=[{"status": "generated", "image_bytes": b"x"}])
        with self.assertRaises(ImageFactoryError):
            build_asset_manifest(book_id="book-001", batch=batch,
                                 results=[{"status": "generated"}])


if __name__ == "__main__":
    unittest.main()
