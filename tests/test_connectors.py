"""Tests de la passerelle PAPI CONNECT : simulation locale, aucun réseau."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from papi_core.connectors import ConnectorError, ConnectorGateway
from papi_core.providers import GenerationRequest, GenerationResult, MockGenerationProvider, ProviderError, ProviderPolicy


class StaticLocalAdapter:
    name = "local-test"
    supported_kinds = frozenset({"text"})
    is_external = False
    credentials_env = None

    def __init__(self, result):
        self.result = result

    def generate(self, request):
        return self.result


class ConnectorGatewayTests(unittest.TestCase):
    def setUp(self):
        self.gateway = ConnectorGateway()
        self.permissions = {"connectors.generate"}

    @staticmethod
    def _result(
        content="valid local output",
        provider="local-test",
        kind="text",
        cost=0,
        simulated=False,
        digest=None,
    ):
        actual_digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return GenerationResult(
            provider=provider,
            kind=kind,
            content=content,
            content_sha256=actual_digest if digest is None else digest,
            estimated_cost_xof=cost,
            simulated=simulated,
        )

    @staticmethod
    def _local_gateway(tmp_path, result=None, adapter=None):
        catalog = json.loads(Path("data/providers.json").read_text(encoding="utf-8"))
        local = next(provider for provider in catalog["providers"] if provider["id"] == "llm.local")
        local.update(status="enabled", enabled=True, last_verified_at="2026-11-16", owner_approval_required=False)
        catalog_path = Path(tmp_path) / "providers.json"
        catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
        gateway = ConnectorGateway(catalog_path)
        gateway.register_adapter("llm.local", adapter or StaticLocalAdapter(result))
        return gateway

    def test_mock_text_generation_uses_common_gateway(self):
        result = self.gateway.generate("local.mock", GenerationRequest("demo-1", "text", "Test prompt"), self.permissions)
        self.assertTrue(result.simulated)
        self.assertEqual(result.estimated_cost_xof, 0)
        self.assertEqual(result.provider, "mock")

    def test_mock_image_generation_is_marked_as_simulation(self):
        result = self.gateway.generate("local.mock", GenerationRequest("demo-2", "image", "A test image"), self.permissions)
        self.assertTrue(result.simulated)
        self.assertIn("SIMULATION MOCK", result.content)

    def test_missing_agent_permission_is_denied(self):
        with self.assertRaises(ConnectorError):
            self.gateway.generate("local.mock", GenerationRequest("demo-3", "text", "Prompt"), set())

    def test_unknown_provider_is_denied(self):
        with self.assertRaises(ConnectorError):
            self.gateway.generate("unknown.provider", GenerationRequest("demo-4", "text", "Prompt"), self.permissions)

    def test_external_provider_is_denied_even_if_permissions_are_present(self):
        with self.assertRaises(ConnectorError):
            self.gateway.generate("llm.gemini", GenerationRequest("demo-5", "text", "Prompt"), {"llm.generate", "network.api"})

    def test_local_candidate_without_adapter_is_denied(self):
        with self.assertRaises(ConnectorError):
            self.gateway.generate("llm.local", GenerationRequest("demo-6", "text", "Prompt"), {"llm.generate", "runtime.local"})

    def test_cost_above_zero_ceiling_is_denied(self):
        with self.assertRaises(ConnectorError):
            self.gateway.generate("local.mock", GenerationRequest("demo-7", "text", "Prompt", estimated_cost_xof=1), self.permissions)

    def test_adapter_registration_rejects_duplicate_id(self):
        with self.assertRaises(ConnectorError):
            self.gateway.register_adapter("local.mock", MockGenerationProvider())

    def test_adapter_registration_requires_callable_generate(self):
        class MissingGenerateAdapter:
            name = "missing-generate"
            supported_kinds = frozenset({"text"})
            is_external = False
            credentials_env = None
            generate = None

        with self.assertRaisesRegex(ConnectorError, "Fonction d'exécution"):
            self.gateway.register_adapter("llm.invalid", MissingGenerateAdapter())

    def test_external_or_credential_bearing_adapters_cannot_be_registered(self):
        class ExternalAdapter(StaticLocalAdapter):
            is_external = True

        class CredentialBearingAdapter(StaticLocalAdapter):
            credentials_env = "LOCAL_PROVIDER_TOKEN"

        with self.assertRaises(ConnectorError):
            self.gateway.register_adapter("llm.external", ExternalAdapter(self._result()))
        with self.assertRaises(ConnectorError):
            self.gateway.register_adapter("llm.credentialed", CredentialBearingAdapter(self._result()))

    def test_provider_policy_rejects_boolean_cost_and_invalid_allowlists(self):
        policies = (
            ProviderPolicy(max_cost_xof=True),
            ProviderPolicy(allowed_providers="mock"),
            ProviderPolicy(allowed_providers=frozenset()),
            ProviderPolicy(allow_external=1),
        )
        for policy in policies:
            with self.subTest(policy=policy), self.assertRaises(ProviderError):
                policy.validate()

    def test_generation_request_rejects_boolean_numeric_limits(self):
        for kwargs in ({"estimated_cost_xof": True}, {"max_output_chars": True}):
            with self.subTest(kwargs=kwargs):
                request = GenerationRequest("demo-bool", "text", "Prompt", **kwargs)
                with self.assertRaises(ConnectorError):
                    self.gateway.generate("local.mock", request, self.permissions)

    def test_adapter_runtime_errors_are_sanitized_and_not_retried(self):
        class RaisingAdapter(StaticLocalAdapter):
            def __init__(self):
                self.calls = 0

            def generate(self, request):
                self.calls += 1
                raise RuntimeError("private provider diagnostic")

        with tempfile.TemporaryDirectory() as tmp:
            adapter = RaisingAdapter()
            gateway = self._local_gateway(tmp, adapter=adapter)
            with self.assertRaisesRegex(ConnectorError, "Échec d'exécution") as raised:
                gateway.generate(
                    "llm.local",
                    GenerationRequest("demo-error", "text", "Prompt"),
                    {"llm.generate", "runtime.local"},
                )
            self.assertEqual(str(raised.exception), "Échec d'exécution de l'adaptateur.")
            self.assertIsNone(raised.exception.__cause__)
            self.assertNotIn("private provider diagnostic", str(raised.exception))
            self.assertEqual(adapter.calls, 1)

    def test_adapter_result_digest_is_verified(self):
        bad_result = self._result(digest="0" * 64)
        with tempfile.TemporaryDirectory() as tmp:
            gateway = self._local_gateway(tmp, bad_result)
            with self.assertRaisesRegex(ConnectorError, "SHA-256"):
                gateway.generate(
                    "llm.local",
                    GenerationRequest("demo-digest", "text", "Prompt"),
                    {"llm.generate", "runtime.local"},
                )

    def test_adapter_result_cost_rejects_negative_and_boolean_values(self):
        for cost in (-1, True):
            with self.subTest(cost=cost), tempfile.TemporaryDirectory() as tmp:
                gateway = self._local_gateway(tmp, self._result(cost=cost))
                with self.assertRaisesRegex(ConnectorError, "Coût"):
                    gateway.generate(
                        "llm.local",
                        GenerationRequest("demo-cost", "text", "Prompt"),
                        {"llm.generate", "runtime.local"},
                    )

    def test_adapter_result_must_match_provider_and_request_kind(self):
        for result in (
            self._result(provider="unexpected-provider"),
            self._result(kind="image"),
        ):
            with self.subTest(result=result), tempfile.TemporaryDirectory() as tmp:
                gateway = self._local_gateway(tmp, result)
                with self.assertRaises(ConnectorError):
                    gateway.generate(
                        "llm.local",
                        GenerationRequest("demo-contract", "text", "Prompt"),
                        {"llm.generate", "runtime.local"},
                    )

    def test_adapter_result_must_respect_requested_output_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            gateway = self._local_gateway(tmp, self._result(content="too long"))
            with self.assertRaisesRegex(ConnectorError, "limite de sortie"):
                gateway.generate(
                    "llm.local",
                    GenerationRequest("demo-size", "text", "Prompt", max_output_chars=3),
                    {"llm.generate", "runtime.local"},
                )

    def test_catalog_override_can_disable_mock(self):
        catalog = json.loads(Path("data/providers.json").read_text(encoding="utf-8"))
        mock = next(p for p in catalog["providers"] if p["id"] == "local.mock")
        mock.update(status="disabled", enabled=False)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "providers.json"
            path.write_text(json.dumps(catalog), encoding="utf-8")
            gateway = ConnectorGateway(path)
            with self.assertRaises(ConnectorError):
                gateway.generate("local.mock", GenerationRequest("demo-8", "text", "Prompt"), self.permissions)


if __name__ == "__main__":
    unittest.main()
