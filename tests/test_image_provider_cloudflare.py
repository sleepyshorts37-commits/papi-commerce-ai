import json
import unittest
from unittest.mock import patch
from io import BytesIO
from datetime import datetime, timezone

from papi_core.image_provider_cloudflare import (
    CloudflareImageAdapter, ImageProviderError, InMemoryNeuronQuotaLedger,
    SupabaseNeuronQuotaLedger, QuotaReservation,
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

    def test_generate_many_runs_bounded_batch_and_preserves_order(self):
        jobs = [
            {"prompt": f"page {i}", "model": "@cf/test/image",
             "idempotency_key": f"batch-page-{i:03d}"}
            for i in range(3)
        ]
        batch_adapter = CloudflareImageAdapter(
            account_id="account-123", api_token="test-only-token",
            ledger=self.ledger, model_costs={"@cf/test/image": 30},
            free_tier_confirmed_for_account=True, transport=self.adapter._transport,
            max_concurrency=2,
        )
        results = batch_adapter.generate_many(jobs=jobs, now=self.day)
        self.assertEqual([item["status"] for item in results],
                         ["generated", "generated", "generated"])
        self.assertEqual([item["idempotency_key"] for item in results],
                         [job["idempotency_key"] for job in jobs])
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(self.ledger.snapshot(self.day)["used_estimated_neurons"], 90)

    def test_generate_many_rejects_duplicate_idempotency_before_network(self):
        job = {"prompt": "page", "model": "@cf/test/image",
               "idempotency_key": "same-batch-key"}
        with self.assertRaisesRegex(ImageProviderError, "unique"):
            self.adapter.generate_many(jobs=[job, job], now=self.day)
        self.assertEqual(self.calls, [])

    def test_generate_many_rejects_excessive_concurrency_configuration(self):
        with self.assertRaisesRegex(ImageProviderError, "Concurrence"):
            CloudflareImageAdapter(
                account_id="account-123", api_token="test", ledger=self.ledger,
                model_costs={"@cf/test/image": 10},
                free_tier_confirmed_for_account=True, max_concurrency=17,
                transport=lambda *a, **k: FakeResponse(),
            )

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


    def test_non_reserved_idempotent_states_never_call_cloudflare(self):
        class ExistingStateLedger:
            def __init__(self, status):
                self.status = status
            def reserve(self, **kwargs):
                return QuotaReservation("reservation-001", kwargs["idempotency_key"],
                                        "2026-11-15", 60, self.status)
            def commit(self, reservation):
                raise AssertionError("commit must not run for a closed reservation")
            def release(self, reservation):
                raise AssertionError("release must not run for a closed reservation")

        for state in ("uncertain", "released", "committed", "reused_reserved"):
            with self.subTest(state=state):
                calls = []
                adapter = CloudflareImageAdapter(
                    account_id="account-123", api_token="test-only-token",
                    ledger=ExistingStateLedger(state),
                    model_costs={"@cf/test/image": 60},
                    free_tier_confirmed_for_account=True,
                    transport=lambda *a, **k: calls.append((a, k)) or FakeResponse(),
                )
                with self.assertRaises(ImageProviderError):
                    adapter.generate(prompt="retry must be blocked",
                                     model="@cf/test/image",
                                     idempotency_key="same-idempotency-key",
                                     now=self.day)
                self.assertEqual(calls, [], f"Cloudflare called for state={state}")



class SupabaseQuotaLedgerTests(unittest.TestCase):
    def setUp(self):
        self.ledger = SupabaseNeuronQuotaLedger(
            supabase_url="https://example.supabase.co",
            service_role_key="local-test-secret",
            account_ref="account-123",
            worker_id="PAPI-IMAGE-01",
            daily_limit=100,
        )
        self.responses = []
        self.requests = []

    def fake_urlopen(self, request, timeout):
        self.requests.append(request)
        payload = self.responses.pop(0)
        return BytesIO(json.dumps(payload).encode("utf-8"))

    def test_reserve_calls_transactional_rpc_and_returns_reservation(self):
        self.responses.append([{
            "reservation_id": "00000000-0000-0000-0000-000000000001",
            "reservation_status": "reserved",
            "quota_day": "2026-11-15",
            "reserved_units": 60,
            "consumed_units": 0,
            "daily_limit": 100,
        }])
        with patch("papi_core.image_provider_cloudflare.urlopen", self.fake_urlopen):
            reservation = self.ledger.reserve(
                idempotency_key="image-job-0001", estimated_neurons=60,
                model="@cf/test/image", now=datetime(2026, 11, 15, tzinfo=timezone.utc),
            )
        self.assertEqual(reservation.status, "reserved")
        self.assertEqual(reservation.reservation_id, "00000000-0000-0000-0000-000000000001")
        payload = json.loads(self.requests[0].data.decode("utf-8"))
        self.assertEqual(payload["p_estimated_units"], 60)
        self.assertEqual(payload["p_model"], "@cf/test/image")
        self.assertNotIn("local-test-secret", repr(payload))

    def test_commit_uses_shared_rpc(self):
        self.responses.append(True)
        reservation = QuotaReservation("00000000-0000-0000-0000-000000000001",
                                       "image-job-0001", "2026-11-15", 60, "reserved")
        with patch("papi_core.image_provider_cloudflare.urlopen", self.fake_urlopen):
            result = self.ledger.commit(reservation)
        self.assertEqual(result.status, "committed")
        self.assertTrue(self.requests[0].full_url.endswith("/papi_commit_provider_quota"))

    def test_reserve_preserves_replay_status_from_shared_rpc(self):
        self.responses.append([{
            "reservation_id": "00000000-0000-0000-0000-000000000001",
            "reservation_status": "reused_reserved",
            "quota_day": "2026-11-15",
            "reserved_units": 60,
            "consumed_units": 0,
            "daily_limit": 100,
        }])
        with patch("papi_core.image_provider_cloudflare.urlopen", self.fake_urlopen):
            reservation = self.ledger.reserve(
                idempotency_key="image-job-replay-001", estimated_neurons=60,
                model="@cf/test/image", now=datetime(2026, 11, 15, tzinfo=timezone.utc),
            )
        self.assertEqual(reservation.status, "reused_reserved")

    def test_mark_uncertain_and_release_use_dedicated_rpc_endpoints(self):
        reservation = QuotaReservation("00000000-0000-0000-0000-000000000001",
                                       "image-job-0002", "2026-11-15", 20, "reserved")
        self.responses.extend([True, True])
        with patch("papi_core.image_provider_cloudflare.urlopen", self.fake_urlopen):
            self.ledger.mark_uncertain(reservation)
            released = self.ledger.release(reservation)
        self.assertEqual(released.status, "released")
        self.assertTrue(self.requests[0].full_url.endswith("/papi_mark_provider_quota_uncertain"))
        self.assertTrue(self.requests[1].full_url.endswith("/papi_release_provider_quota"))

    def test_shared_ledger_rejects_short_idempotency_key_before_network(self):
        with self.assertRaises(ImageProviderError):
            self.ledger.reserve(idempotency_key="short", estimated_neurons=1,
                                model="@cf/test/image")
        self.assertEqual(self.requests, [])

    def test_configuration_requires_https_and_server_key(self):
        with self.assertRaises(ImageProviderError):
            SupabaseNeuronQuotaLedger(
                supabase_url="http://example.supabase.co",
                service_role_key="secret", account_ref="account-123",
                worker_id="PAPI-IMAGE-01",
            )


if __name__ == "__main__":
    unittest.main()
