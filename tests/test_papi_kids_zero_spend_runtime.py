import base64
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

from PIL import Image

from papi_core.image_campaign import plan_image_campaign
from papi_core.papi_kids_orchestrator import (
    execute_pkp0001_campaign, prepare_pkp0001_from_project_sources,
)
from papi_core.image_provider_registry import (
    ImageProviderRegistry, ModelProfile, ProviderProfile,
)
from papi_core.papi_kids_asset_center_adapter import PapiKidsIllustrationAssetCenter
from papi_core.papi_kids_image_batch_adapter import CloudflareFluxSchnellBatchAdapter
from papi_core.papi_kids_image_provider import (
    MODEL_ID, CloudflareFluxSchnellProvider,
)
from papi_core.papi_kids_zero_spend_runtime import build_pkp0001_zero_spend_runtime_engine


UPLOAD_ID = "PKP-UP-" + "a" * 32


def jpeg_bytes(size=(1024, 1024)):
    image = Image.new("RGB", size, (110, 130, 150))
    stream = BytesIO()
    image.save(stream, format="JPEG")
    return stream.getvalue()


def free_evidence():
    now = datetime.now(timezone.utc)
    return {
        "provider": "cloudflare_workers_ai",
        "model_id": MODEL_ID,
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
        self.counter = 0
        self.reservations = []
        self.settlements = []

    def reserve(self, evidence, **kwargs):
        self.counter += 1
        self.reservations.append(kwargs)
        return f"reservation-{self.counter}"

    def settle(self, evidence, **kwargs):
        self.settlements.append(kwargs)


class PapiKidsImageWiringTests(unittest.TestCase):
    def test_private_asset_center_registers_and_resumes_by_idempotency(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / UPLOAD_ID).mkdir()
            registered = []
            center = PapiKidsIllustrationAssetCenter(
                root, upload_id=UPLOAD_ID,
                asset_registrar=lambda metadata: registered.append(metadata["asset_id"]),
            )
            image = jpeg_bytes((32, 32))
            record = center.put(
                book_id="PKP-0001", page_id="page-01", page_number=1,
                idempotency_key="a" * 64, image_bytes=image,
                content_type="image/jpeg", model=MODEL_ID, prompt_sha256="b" * 64,
            )
            self.assertEqual(record["persistence_status"], "registered")
            existing = center.get(
                book_id="PKP-0001", page_id="page-01", page_number=1,
                idempotency_key="a" * 64,
            )
            self.assertEqual(existing["asset_id"], record["asset_id"])
            self.assertEqual(len(registered), 2)

    def test_new_prompt_creates_new_version_but_same_key_is_idempotent(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / UPLOAD_ID).mkdir()
            center = PapiKidsIllustrationAssetCenter(root, upload_id=UPLOAD_ID,
                                                     asset_registrar=lambda metadata: None)
            center.put(
                book_id="PKP-0001", page_id="page-01", page_number=1,
                idempotency_key="a" * 64, image_bytes=jpeg_bytes((32, 32)),
                content_type="image/jpeg", model=MODEL_ID, prompt_sha256="b" * 64,
            )
            self.assertIsNone(center.get(
                book_id="PKP-0001", page_id="page-01", page_number=1,
                idempotency_key="c" * 64,
            ))
            second = center.put(
                book_id="PKP-0001", page_id="page-01", page_number=1,
                idempotency_key="c" * 64, image_bytes=jpeg_bytes((32, 32)),
                content_type="image/jpeg", model=MODEL_ID, prompt_sha256="d" * 64,
            )
            self.assertEqual(second["version"], 2)

    def test_batch_adapter_stops_after_first_provider_error(self):
        class Provider:
            def __init__(self):
                self.calls = []
                self.reservation_store = Mock()
                self.account_id = "a" * 32
            def generate(self, prompt, **kwargs):
                self.calls.append(prompt)
                raise RuntimeError("quota refused")
        provider = Provider()
        adapter = CloudflareFluxSchnellBatchAdapter(
            provider=provider, quota_evidence=free_evidence(), generation_authorized=True,
        )
        jobs = [{
            "prompt": f"page {i}", "model": MODEL_ID, "idempotency_key": f"key-{i}",
            "batch_id": "campaign-01", "page_number": i,
        } for i in range(1, 4)]
        result = adapter.generate_many(jobs=jobs)
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual([x["status"] for x in result], ["failed", "failed", "failed"])
        self.assertTrue(all(x["fallback_used"] is False for x in result))

    def test_runtime_construction_never_calls_provider_and_is_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / UPLOAD_ID).mkdir()
            registry = ImageProviderRegistry(
                providers=[ProviderProfile("cloudflare", "Cloudflare", "https://developers.cloudflare.com/workers-ai/platform/pricing", "verified", "account_api", True)],
                models=[ModelProfile("cloudflare", MODEL_ID, "image", 58, True, True, True)],
            )
            transport = Mock()
            engine, report = build_pkp0001_zero_spend_runtime_engine(
                upload_id=UPLOAD_ID, storage_root=root, registry=registry,
                account_refs={"cloudflare": "a" * 32},
                quota_evidence_by_model={MODEL_ID: free_evidence()},
                operator_confirmed_free_tier=True, generation_authorized=False,
                account_id="a" * 32, api_token="server-secret",
                reservation_store=FakeReservationStore(),
                asset_registrar=lambda metadata: None,
                transport=transport,
            )
            self.assertIsNotNone(engine)
            self.assertFalse(report["generation_authorized"])
            self.assertFalse(report["network_called"])
            transport.assert_not_called()

    def test_authorized_engine_generates_and_registers_a_small_batch_with_mock_transport(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / UPLOAD_ID).mkdir()
            registry = ImageProviderRegistry(
                providers=[ProviderProfile("cloudflare", "Cloudflare", "https://developers.cloudflare.com/workers-ai/platform/pricing", "verified", "account_api", True)],
                models=[ModelProfile("cloudflare", MODEL_ID, "image", 58, True, True, True)],
            )
            image = jpeg_bytes()
            transport = Mock(return_value=(200, json.dumps({
                "success": True, "result": {"image": base64.b64encode(image).decode("ascii")}
            }).encode()))
            reservation = FakeReservationStore()
            registered = []
            engine, report = build_pkp0001_zero_spend_runtime_engine(
                upload_id=UPLOAD_ID, storage_root=root, registry=registry,
                account_refs={"cloudflare": "a" * 32},
                quota_evidence_by_model={MODEL_ID: free_evidence()},
                operator_confirmed_free_tier=True, generation_authorized=False,
                account_id="a" * 32, api_token="server-secret",
                reservation_store=reservation,
                asset_registrar=lambda metadata: registered.append(metadata["asset_id"]),
                transport=transport, max_batch_size=4,
            )
            prepared = prepare_pkp0001_from_project_sources(
                project_root=root, registry=registry,
                account_refs={"cloudflare": "a" * 32},
                quota_evidence_by_model={MODEL_ID: report["registry_quota_evidence"]},
            )
            result = execute_pkp0001_campaign(
                prepared=prepared, engine=engine,
                quota_evidence=report["registry_quota_evidence"],
                generation_authorized=True, spend_limit_minor=0,
                max_batches_per_run=1,
            )
            execution = result["execution"]
            self.assertEqual(execution["batch_reports"][0]["stored_count"], 4)
            self.assertEqual(transport.call_count, 4)
            self.assertEqual(len(registered), 4)
            self.assertEqual(len(reservation.reservations), 4)
            self.assertEqual(len(reservation.settlements), 4)
            self.assertEqual(result["human_review_required"], True)


if __name__ == "__main__":
    unittest.main()
