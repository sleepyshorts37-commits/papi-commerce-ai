import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from papi_core.image_asset_center import LocalImageAssetCenter
from papi_core.image_provider_registry import ImageProviderRegistry, ModelProfile, ProviderProfile
from papi_core.papi_kids_runtime import PapiKidsRuntimeError, build_pkp0001_runtime_engine


def proof():
    now = datetime.now(timezone.utc)
    return {
        "provider": "cloudflare", "account_ref": "cf-test-account",
        "model_id": "@cf/test/image",
        "source_url": "https://developers.cloudflare.com/workers-ai/platform/pricing/",
        "evidence_ref": "runtime-test",
        "verified_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=12)).isoformat(),
        "daily_quota_units": 1000, "spend_cap_minor": 0,
    }


class PapiKidsRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        provider = ProviderProfile(
            "cloudflare", "Cloudflare",
            "https://developers.cloudflare.com/workers-ai/platform/pricing/",
            "reviewed", "account_api", default_enabled=True)
        model = ModelProfile(
            "cloudflare", "@cf/test/image", "image", 4,
            commercial_use_reviewed=True, output_policy_reviewed=True, enabled=True)
        self.registry = ImageProviderRegistry(providers=[provider], models=[model])
        self.env = {
            "SUPABASE_URL": "https://test-project.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test-secret-only",
            "CLOUDFLARE_ACCOUNT_ID": "cf-test-account",
            "CLOUDFLARE_API_TOKEN": "cf-test-token",
            "PAPI_WORKER_ID": "PAPI-TEST-01",
            "PAPI_CLOUDFLARE_DAILY_NEURON_LIMIT": "1000",
        }

    def test_builds_server_runtime_without_network_call(self):
        called = []
        def transport(*args, **kwargs):
            called.append(True)
            raise AssertionError("Runtime construction must not call provider.")
        with patch.dict(os.environ, self.env, clear=True):
            engine, info = build_pkp0001_runtime_engine(
                registry=self.registry,
                account_refs={"cloudflare": "cf-test-account"},
                quota_evidence_by_model={"@cf/test/image": proof()},
                asset_center=LocalImageAssetCenter(Path(self.temp.name) / "assets"),
                operator_confirmed_free_tier=True,
                transport=transport,
            )
        self.assertEqual(info["quota_ledger"], "supabase_transactional_shared")
        self.assertFalse(info["network_called"])
        self.assertEqual(called, [])
        self.assertEqual(engine.generator.models[0].model_id, "@cf/test/image")

    def test_requires_operator_confirmation_and_server_secrets(self):
        with patch.dict(os.environ, self.env, clear=True):
            with self.assertRaises(PapiKidsRuntimeError):
                build_pkp0001_runtime_engine(
                    registry=self.registry,
                    account_refs={"cloudflare": "cf-test-account"},
                    quota_evidence_by_model={"@cf/test/image": proof()},
                    asset_center=LocalImageAssetCenter(Path(self.temp.name) / "a"),
                    operator_confirmed_free_tier=False,
                )
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(PapiKidsRuntimeError, "SUPABASE_URL"):
                build_pkp0001_runtime_engine(
                    registry=self.registry,
                    account_refs={"cloudflare": "cf-test-account"},
                    quota_evidence_by_model={"@cf/test/image": proof()},
                    asset_center=LocalImageAssetCenter(Path(self.temp.name) / "b"),
                    operator_confirmed_free_tier=True,
                )


if __name__ == "__main__":
    unittest.main()
