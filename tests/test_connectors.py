"""Tests de la passerelle PAPI CONNECT : simulation locale, aucun réseau."""
import json
import tempfile
import unittest
from pathlib import Path
from papi_core.connectors import ConnectorError, ConnectorGateway
from papi_core.providers import GenerationRequest, MockGenerationProvider

class ConnectorGatewayTests(unittest.TestCase):
    def setUp(self):
        self.gateway = ConnectorGateway()
        self.permissions = {"connectors.generate"}

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

    def test_external_provider_is_denied_even_if_registered(self):
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
