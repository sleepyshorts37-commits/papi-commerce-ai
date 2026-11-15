import unittest

from papi_core.image_campaign import (
    ImageCampaignError, execute_image_campaign, plan_image_campaign,
)
from papi_core.image_production_engine import ImageProductionEngine


PNG = b"\x89PNG\r\n\x1a\n" + b"campaign-test"


class MemoryAssets:
    def __init__(self):
        self.items = {}

    def get(self, *, book_id, page_id, idempotency_key):
        return self.items.get(idempotency_key)

    def put(self, *, book_id, page_id, page_number, idempotency_key,
            image_bytes, content_type, model, prompt_sha256):
        item = {"book_id": book_id, "page_id": page_id,
                "idempotency_key": idempotency_key}
        self.items[idempotency_key] = item
        return item


class Generator:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def generate_many(self, *, jobs, now=None):
        self.calls += 1
        return [
            ({"status": "failed", "idempotency_key": job["idempotency_key"],
              "error": "mock"} if self.fail else
             {"status": "generated", "idempotency_key": job["idempotency_key"],
              "image_bytes": PNG, "content_type": "image/png"})
            for job in jobs
        ]


class ImageCampaignTests(unittest.TestCase):
    def setUp(self):
        self.books = [
            {"book_id": "book-a", "pages": [
                {"page_id": "a-1", "page_number": 1, "prompt": "Page A1"},
                {"page_id": "a-2", "page_number": 2, "prompt": "Page A2"},
            ]},
            {"book_id": "book-b", "pages": [
                {"page_id": "b-1", "page_number": 1, "prompt": "Page B1"},
                {"page_id": "b-2", "page_number": 2, "prompt": "Page B2"},
            ]},
        ]
        self.plan = plan_image_campaign(
            campaign_id="series-01", books=self.books,
            model="@cf/test/image", model_costs={"@cf/test/image": 5},
            max_batch_size=2, max_batch_units=10,
        )

    def test_plans_multiple_books_deterministically(self):
        again = plan_image_campaign(
            campaign_id="series-01", books=self.books,
            model="@cf/test/image", model_costs={"@cf/test/image": 5},
            max_batch_size=2, max_batch_units=10,
        )
        self.assertEqual(self.plan["book_count"], 2)
        self.assertEqual(self.plan["page_count"], 4)
        self.assertEqual(
            [b.batch_id for b in self.plan["batches"]],
            [b.batch_id for b in again["batches"]],
        )

    def test_bounded_run_can_resume_without_regenerating_saved_images(self):
        assets, generator = MemoryAssets(), Generator()
        engine = ImageProductionEngine(generator=generator, asset_center=assets)
        first = execute_image_campaign(plan=self.plan, engine=engine, max_batches_per_run=1)
        self.assertFalse(first["complete"])
        self.assertEqual(first["remaining_batch_count"], 1)
        second = execute_image_campaign(
            plan=self.plan, engine=engine, max_batches_per_run=1,
            start_batch_index=first["next_batch_index"],
        )
        self.assertTrue(second["complete"])
        self.assertEqual(generator.calls, 2)
        self.assertEqual(len(assets.items), 4)

    def test_failed_batch_halts_and_can_be_blocked_on_resume(self):
        engine = ImageProductionEngine(generator=Generator(fail=True), asset_center=MemoryAssets())
        first = execute_image_campaign(plan=self.plan, engine=engine, max_batches_per_run=2)
        self.assertEqual(len(first["halted_batch_ids"]), 1)
        self.assertTrue(first["human_reconciliation_required"])
        blocked = set(first["blocked_batch_ids_to_persist"])
        second = execute_image_campaign(
            plan=self.plan, engine=engine, max_batches_per_run=2,
            blocked_batch_ids=blocked,
        )
        self.assertIn(first["halted_batch_ids"][0], second["skipped_blocked_batch_ids"])

    def test_rejects_duplicate_book_ids(self):
        with self.assertRaises(ImageCampaignError):
            plan_image_campaign(
                campaign_id="series-02", books=[self.books[0], self.books[0]],
                model="@cf/test/image", model_costs={"@cf/test/image": 5},
            )


if __name__ == "__main__":
    unittest.main()
