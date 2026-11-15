import base64
import json
import unittest
from datetime import datetime, timedelta, timezone
from io import BytesIO
from unittest.mock import Mock

from PIL import Image

from papi_core.papi_kids_image_provider import (
    CloudflareFluxSchnellProvider, ImageProviderBlocked,
    estimate_flux_schnell_neurons, validate_free_quota_evidence,
)


def jpeg_bytes():
    image = Image.new("RGB", (1024, 1024), (120, 140, 160))
    stream = BytesIO()
    image.save(stream, format="JPEG")
    return stream.getvalue()


def evidence():
    now = datetime.now(timezone.utc)
    return {
        "provider": "cloudflare_workers_ai",
        "model_id": "@cf/black-forest-labs/flux-1-schnell",
        "account_plan": "workers_free",
        "daily_limit_neurons": 10000.0,
        "remaining_neurons": 5000.0,
        "account_fingerprint": "a" * 64,
        "evidence_ref": "cloudflare-dashboard-snapshot-001",
        "quota_checked_at": now.isoformat(),
        "evidence_expires_at": (now + timedelta(hours=1)).isoformat(),
        "usage_date": now.date().isoformat(),
        "model_access_confirmed": True,
        "commercial_license_confirmed": True,
        "zero_spend_confirmed": True,
        "cost_limit_minor": 0,
    }


class FakeReservationStore:
    def __init__(self):
        self.reserved = []
        self.settled = []

    def reserve(self, evidence, **kwargs):
        self.reserved.append(kwargs)
        return "reservation-001"

    def settle(self, evidence, **kwargs):
        self.settled.append(kwargs)


class PapiKidsCloudflareProviderTests(unittest.TestCase):
    def test_estimates_neurons_for_24_square_images(self):
        per_image = estimate_flux_schnell_neurons(1024, 1024, 4)
        self.assertEqual(per_image, 76.8)
        self.assertEqual(round(per_image * 24, 1), 1843.2)

    def test_rejects_paid_plan_and_spend(self):
        proof = evidence()
        proof["account_plan"] = "workers_paid"
        with self.assertRaises(ImageProviderBlocked):
            validate_free_quota_evidence(proof, required_neurons=76.8)
        proof = evidence()
        proof["zero_spend_confirmed"] = False
        with self.assertRaises(ImageProviderBlocked):
            validate_free_quota_evidence(proof, required_neurons=76.8)

    def test_rejects_stale_or_insufficient_quota(self):
        proof = evidence()
        proof["remaining_neurons"] = 1
        with self.assertRaises(ImageProviderBlocked):
            validate_free_quota_evidence(proof, required_neurons=76.8)
        proof = evidence()
        proof["evidence_expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        with self.assertRaises(ImageProviderBlocked):
            validate_free_quota_evidence(proof, required_neurons=76.8)

    def test_no_external_call_without_explicit_authorization(self):
        store = FakeReservationStore()
        transport = Mock()
        provider = CloudflareFluxSchnellProvider(
            account_id="account", api_token="secret", reservation_store=store, transport=transport,
        )
        with self.assertRaises(ImageProviderBlocked):
            provider.generate("a child-friendly river illustration", evidence=evidence(),
                              allow_generation=False, campaign_id="PKP-0001", page_number=1)
        transport.assert_not_called()
        self.assertEqual(store.reserved, [])

    def test_generates_with_fresh_free_quota_and_no_fallback(self):
        store = FakeReservationStore()
        image = jpeg_bytes()
        transport = Mock(return_value=(200, json.dumps({
            "success": True, "result": {"image": base64.b64encode(image).decode("ascii")}
        }).encode()))
        provider = CloudflareFluxSchnellProvider(
            account_id="account", api_token="server-token",
            reservation_store=store, transport=transport,
        )
        result = provider.generate(
            "a child-friendly river illustration", evidence=evidence(),
            allow_generation=True, campaign_id="PKP-0001", page_number=1,
        )
        self.assertEqual(result["width_px"], 1024)
        self.assertEqual(result["estimated_neurons"], 76.8)
        self.assertEqual(result["cost_minor"], 0)
        self.assertFalse(result["print_ready_300dpi"])
        self.assertFalse(result["fallback_used"])
        self.assertEqual(len(store.reserved), 1)
        self.assertEqual(store.settled[0]["consumed"], True)

    def test_failed_http_attempt_is_counted_and_never_falls_back(self):
        store = FakeReservationStore()
        transport = Mock(return_value=(429, b'{"success":false}'))
        provider = CloudflareFluxSchnellProvider(
            account_id="account", api_token="server-token",
            reservation_store=store, transport=transport,
        )
        with self.assertRaises(ImageProviderBlocked):
            provider.generate(
                "a child-friendly river illustration", evidence=evidence(),
                allow_generation=True, campaign_id="PKP-0001", page_number=1,
            )
        self.assertTrue(store.settled[0]["consumed"])
        self.assertIsNone(store.settled[0]["output_sha256"])


if __name__ == "__main__":
    unittest.main()
