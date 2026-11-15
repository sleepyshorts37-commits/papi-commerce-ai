import unittest

from papi_core.image_model_router import (
    FreeImageModel, FreeImageModelRouter, ImageModelRoutingError,
    calculate_throughput,
)


class FakeProvider:
    def __init__(self, *, clock_results=None):
        self.calls = []
    def generate_many(self, *, jobs, now=None):
        self.calls.append(jobs)
        return [
            {"status": "generated", "idempotency_key": job["idempotency_key"],
             "image_bytes": b"image", "model": job["model"]}
            for job in jobs
        ]


class ImageModelRouterTests(unittest.TestCase):
    def setUp(self):
        self.provider = FakeProvider()
        ticks = iter([10.0, 13.0])
        self.router = FreeImageModelRouter(
            provider=self.provider,
            models=[
                FreeImageModel("@cf/model-expensive", 120, True),
                FreeImageModel("@cf/model-cheap", 40, True),
            ],
            clock=lambda: next(ticks),
        )

    def test_selects_lowest_estimated_cost_free_model(self):
        jobs = [{"prompt": f"page {i}", "idempotency_key": f"book-page-{i:03d}"}
                for i in range(4)]
        results = self.router.generate_many(jobs=jobs)
        self.assertEqual(len(results), 4)
        self.assertEqual(len(self.provider.calls), 1)
        self.assertTrue(all(job["model"] == "@cf/model-cheap" for job in self.provider.calls[0]))
        metrics = self.router.last_metrics
        self.assertEqual(metrics["generated_images"], 4)
        self.assertEqual(metrics["elapsed_seconds"], 3.0)
        self.assertEqual(metrics["images_per_hour"], 4800.0)
        self.assertFalse(metrics["paid_fallback_used"])

    def test_rejects_unconfirmed_model(self):
        with self.assertRaisesRegex(ImageModelRoutingError, "non confirmé"):
            FreeImageModelRouter(
                provider=self.provider,
                models=[FreeImageModel("@cf/not-confirmed", 10, False)],
            )
        self.assertEqual(self.provider.calls, [])

    def test_rejects_duplicate_keys_before_provider(self):
        job = {"prompt": "image", "idempotency_key": "duplicate"}
        with self.assertRaisesRegex(ImageModelRoutingError, "dupliquée"):
            self.router.generate_many(jobs=[job, job])
        self.assertEqual(self.provider.calls, [])

    def test_throughput_formula_uses_actual_count_and_duration(self):
        self.assertEqual(
            calculate_throughput(generated_images=10, elapsed_seconds=30)["images_per_hour"],
            1200.0,
        )
        with self.assertRaises(ImageModelRoutingError):
            calculate_throughput(generated_images=1, elapsed_seconds=0)


if __name__ == "__main__":
    unittest.main()
