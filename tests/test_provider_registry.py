"""Tests for PAPI CONNECT provider registry; local-only, no network."""
import tempfile
import unittest
from pathlib import Path
from papi_core.provider_registry import ProviderRegistryError, authorize_provider, find_providers, load_provider_catalog, validate_catalog

class ProviderRegistryTests(unittest.TestCase):
    def test_catalog_is_valid_and_entries_start_disabled(self):
        catalog = load_provider_catalog()
        self.assertGreaterEqual(len(catalog["providers"]), 6)
        self.assertTrue(all(p["status"] == "proposed" and not p["enabled"] for p in catalog["providers"]))

    def test_capability_search_is_read_only(self):
        results = find_providers(capability="text.generate")
        self.assertIn("llm.gemini", {p["id"] for p in results})
        self.assertTrue(all(not p["enabled"] for p in results))

    def test_duplicate_provider_ids_are_rejected(self):
        catalog = load_provider_catalog()
        catalog["providers"].append(dict(catalog["providers"][0]))
        self.assertTrue(any("Duplicate" in e for e in validate_catalog(catalog)))

    def test_unknown_status_is_rejected(self):
        catalog = load_provider_catalog()
        catalog["providers"][0]["status"] = "active"
        self.assertTrue(validate_catalog(catalog))

    def test_secret_value_is_not_accepted_as_env_variable_name(self):
        catalog = load_provider_catalog()
        catalog["providers"][0]["credentials_env"] = ["AIza-this-is-a-secret-value"]
        self.assertTrue(validate_catalog(catalog))

    def test_enabled_flag_and_status_must_match(self):
        catalog = load_provider_catalog()
        catalog["providers"][0]["enabled"] = True
        self.assertTrue(validate_catalog(catalog))

    def test_proposed_provider_cannot_be_authorized(self):
        provider = load_provider_catalog()["providers"][0]
        with self.assertRaises(ProviderRegistryError):
            authorize_provider(provider, {"llm.generate", "network.api"}, owner_approved=True)

    def test_missing_agent_permission_is_rejected(self):
        provider = load_provider_catalog()["providers"][0]
        provider.update(status="enabled", enabled=True, last_verified_at="2026-11-16")
        with self.assertRaises(ProviderRegistryError):
            authorize_provider(provider, set(), owner_approved=True)

    def test_external_provider_requires_owner_approval(self):
        provider = load_provider_catalog()["providers"][0]
        provider.update(status="enabled", enabled=True, last_verified_at="2026-11-16")
        with self.assertRaises(ProviderRegistryError):
            authorize_provider(provider, {"llm.generate", "network.api"}, owner_approved=False)

    def test_invalid_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "providers.json"
            path.write_text("{bad json", encoding="utf-8")
            with self.assertRaises(ProviderRegistryError):
                load_provider_catalog(path)

if __name__ == "__main__":
    unittest.main()
