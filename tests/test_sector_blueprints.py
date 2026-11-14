import unittest

from papi_core.sector_blueprints import (
    SectorBlueprintError,
    get_sector_blueprint,
    list_sector_blueprints,
    validate_sector_facts,
)


class SectorBlueprintTests(unittest.TestCase):
    def test_six_supported_sectors_are_listed(self):
        sectors = list_sector_blueprints()
        self.assertEqual(len(sectors), 6)
        self.assertEqual(
            {item["industry"] for item in sectors},
            {"corporate", "ecommerce", "hospitality", "professional_services", "education", "health"},
        )

    def test_blueprint_returns_defensive_copy(self):
        first = get_sector_blueprint("hospitality")
        first["pages"].clear()
        self.assertEqual(len(get_sector_blueprint("hospitality")["pages"]), 4)

    def test_unknown_sector_is_rejected(self):
        with self.assertRaises(SectorBlueprintError):
            get_sector_blueprint("../health")

    def test_missing_facts_are_reported_without_claiming_truth(self):
        result = validate_sector_facts("ecommerce", {"catalogue réel": "Catalogue communiqué"})
        self.assertFalse(result["complete"])
        self.assertIn("prix et devise", result["missing_facts"])
        self.assertFalse(result["truth_verified"])
        self.assertTrue(result["human_verification_required"])

    def test_complete_fact_labels_still_require_human_verification(self):
        blueprint = get_sector_blueprint("education")
        facts = {label: "À vérifier par le responsable" for label in blueprint["required_facts"]}
        result = validate_sector_facts("education", facts)
        self.assertTrue(result["complete"])
        self.assertFalse(result["truth_verified"])
        self.assertTrue(result["human_verification_required"])

    def test_invalid_fact_container_is_rejected(self):
        with self.assertRaises(SectorBlueprintError):
            validate_sector_facts("health", ["invalid"])

    def test_health_guardrails_are_explicit(self):
        rules = " ".join(get_sector_blueprint("health")["guardrails"]).lower()
        self.assertIn("guérison", rules)
        self.assertIn("posologie", rules)


if __name__ == "__main__":
    unittest.main()
