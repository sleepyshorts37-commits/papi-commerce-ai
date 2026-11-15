import unittest
from datetime import datetime, timezone

from papi_core.image_provider_cloudflare import (
    CloudflareImageAdapter, ImageProviderError, InMemoryNeuronQuotaLedger,
)


class FakeResponse:
    status_code = 200
    headers = {"content-type": "image/png"}
    content = b"fake-png-bytes"


class CloudflareQuotaTests(unittest.TestCase):
    def setUp(self):
        self.day = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
        self.ledger = InMemoryNeuronQuotaLedger(daily_limit=100)
        self.calls = []
        def transport(url, *, headers, json_body, timeout):
            self.calls.append((url, headers, json_body, timeout))
            return FakeResponse()
        self.adapter = CloudflareImageAdapter(
            account_id="account-123", api_token="test-only-token",
            ledger=self.ledger, model_costs={"@cf/test/image": 60},
            free_tier_confirmed_for_account=True, transport=transport,
        )

    def test_success_reserves_then_commits_estimated_usage(self):
        result = self.adapter.generate(
            prompt="A test illustration", model="@cf/test/image",
            idempotency_key="book-page-01", now=self.day,
        )
        self.assertEqual(result["image_bytes"], b"fake-png-bytes")
        self.assertFalse(result["paid_fallback_used"])
        snapshot = self.ledger.snapshot(self.day)
        self.assertEqual(snapshot["used_estimated_neurons"], 60)
        self.assertEqual(snapshot["available_estimated_neurons"], 40)
        self.assertEqual(len(self.calls), 1)
        self.assertNotIn("test-only-token", repr(result))

    def test_quota_exhaustion_blocks_before_network(self):
        self.adapter.generate(prompt="one", model="@cf/test/image",
                              idempotency_key="first-job", now=self.day)
        with self.assertRaises(ImageProviderError):
            self.adapter.generate(prompt="two", model="@cf/test/image",
                                  idempotency_key="second-job", now=self.day)
        self.assertEqual(len(self.calls), 1)

    def test_unknown_model_blocks_before_network(self):
        with self.assertRaises(ImageProviderError):
            self.adapter.generate(prompt="x", model="@cf/unknown",
                                  idempotency_key="unknown-job", now=self.day)
        self.assertEqual(self.calls, [])

    def test_unconfirmed_free_tier_is_blocked_at_construction(self):
        with self.assertRaises(ImageProviderError):
            CloudflareImageAdapter(
                account_id="account-123", api_token="test",
                ledger=self.ledger, model_costs={"@cf/test/image": 10},
                free_tier_confirmed_for_account=False, transport=lambda *a, **k: FakeResponse(),
            )

    def test_missing_model_cost_is_rejected(self):
        with self.assertRaises(ImageProviderError):
            CloudflareImageAdapter(
                account_id="account-123", api_token="test",
                ledger=self.ledger, model_costs={},
                free_tier_confirmed_for_account=True,
                transport=lambda *a, **k: FakeResponse(),
            )

    def test_ambiguous_network_error_keeps_reservation(self):
        def broken(*args, **kwargs):
            raise TimeoutError("simulated timeout")
        adapter = CloudflareImageAdapter(
            account_id="account-123", api_token="test", ledger=self.ledger,
            model_costs={"@cf/test/image": 60},
            free_tier_confirmed_for_account=True, transport=broken,
        )
        with self.assertRaisesRegex(ImageProviderError, "réservé conservé"):
            adapter.generate(prompt="x", model="@cf/test/image",
                             idempotency_key="timeout-job", now=self.day)
        snap = self.ledger.snapshot(self.day)
        self.assertEqual(snap["reserved_estimated_neurons"], 60)
        self.assertEqual(snap["used_estimated_neurons"], 0)

    def test_utc_daily_reset(self):
        next_day = datetime(2026, 11, 16, 0, 1, tzinfo=timezone.utc)
        self.adapter.generate(prompt="x", model="@cf/test/image",
                              idempotency_key="day-one", now=self.day)
        self.assertEqual(self.ledger.snapshot(next_day)["available_estimated_neurons"], 100)

    def test_reservations_are_idempotent(self):
        first = self.ledger.reserve(idempotency_key="same-key", estimated_neurons=25, now=self.day)
        second = self.ledger.reserve(idempotency_key="same-key", estimated_neurons=25, now=self.day)
        self.assertEqual(first, second)
        self.assertEqual(self.ledger.snapshot(self.day)["reserved_estimated_neurons"], 25)

    def test_concurrent_reservations_cannot_overdraw(self):
        import threading
        outcomes = []
        def reserve(i):
            try:
                self.ledger.reserve(idempotency_key=f"parallel-{i}", estimated_neurons=60, now=self.day)
                outcomes.append("ok")
            except ImageProviderError:
                outcomes.append("blocked")
        threads = [threading.Thread(target=reserve, args=(i,)) for i in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertCountEqual(outcomes, ["ok", "blocked"])
        self.assertEqual(self.ledger.snapshot(self.day)["reserved_estimated_neurons"], 60)


if __name__ == "__main__":
    unittest.main()
