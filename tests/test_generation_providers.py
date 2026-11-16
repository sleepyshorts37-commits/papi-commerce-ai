"""Tests des interfaces fournisseurs : aucune connexion réseau ni dépense."""
import unittest

from papi_core.providers import (
    GenerationRequest, MockGenerationProvider, ProviderError,
    ProviderPolicy, ProviderRegistry,
)


class GenerationProviderTests(unittest.TestCase):
    def test_default_registry_runs_only_explicit_mock_simulation(self):
        result = ProviderRegistry().generate(
            "mock", GenerationRequest("PKP-0123456789abcdef", "text", "Écris une histoire.")
        )
        self.assertTrue(result.simulated)
        self.assertEqual(result.estimated_cost_xof, 0)
        self.assertIn("SIMULATION MOCK", result.content)

    def test_unknown_or_unallowed_provider_is_rejected(self):
        registry = ProviderRegistry()
        with self.assertRaises(ProviderError):
            registry.generate("unknown", GenerationRequest("p1", "text", "prompt"))

    def test_external_provider_cannot_be_enabled_without_owner_approval(self):
        with self.assertRaises(ProviderError):
            ProviderPolicy(allow_external=True, owner_approved=False).validate()

    def test_cost_limit_blocks_generation(self):
        registry = ProviderRegistry(ProviderPolicy(max_cost_xof=0))
        request = GenerationRequest("p1", "text", "prompt", estimated_cost_xof=1)
        with self.assertRaises(ProviderError):
            registry.generate("mock", request)

    def test_invalid_kind_and_empty_prompt_are_rejected(self):
        registry = ProviderRegistry()
        with self.assertRaises(ProviderError):
            registry.generate("mock", GenerationRequest("p1", "video", "prompt"))
        with self.assertRaises(ProviderError):
            registry.generate("mock", GenerationRequest("p1", "text", " "))

    def test_mock_output_is_deterministic_and_marked_simulated(self):
        provider = MockGenerationProvider()
        request = GenerationRequest("p1", "image", "Un renard dans une forêt")
        first = provider.generate(request)
        second = provider.generate(request)
        self.assertEqual(first.content_sha256, second.content_sha256)
        self.assertTrue(first.simulated)


if __name__ == "__main__":
    unittest.main()
