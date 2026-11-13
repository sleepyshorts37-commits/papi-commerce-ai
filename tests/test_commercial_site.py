import tempfile
import unittest
from pathlib import Path

from papi_core.commercial_site import CommercialSiteError, generate_commercial_site


class CommercialSiteIntegrationTests(unittest.TestCase):
    def brief(self, **updates):
        value = {
            "content_type": "business_page",
            "sector": "hotel",
            "brand": "Hôtel Baobab",
            "offer": "Séjour en bord de mer",
            "audience": "voyageurs",
            "facts": ["Établissement situé à Saly", "Restaurant sur place"],
            "tone": "professional",
            "cta": "Contactez la réception pour confirmer les disponibilités.",
        }
        value.update(updates)
        return value

    def test_generates_static_site_from_validated_content(self):
        with tempfile.TemporaryDirectory() as directory:
            result = generate_commercial_site(directory, "hotel-baobab", self.brief())
            root = Path(directory) / "hotel-baobab"
            html = (root / "index.html").read_text(encoding="utf-8")
            self.assertTrue(result["quality"]["passed"])
            self.assertIn("Établissement situé à Saly", html)
            self.assertIn("disponibilités", html)
            self.assertTrue(result["review_required"])
            self.assertFalse(result["published"])
            self.assertFalse(result["network_used"])
            self.assertEqual(set(result["files"]), {"index.html", "styles.css", "project.json"})

    def test_rejects_markup_before_site_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                generate_commercial_site(
                    directory, "safe-hotel",
                    self.brief(facts=["Vue <script>alert(1)</script>"]),
                )
            self.assertFalse((Path(directory) / "safe-hotel").exists())

    def test_refuses_oversized_content_without_creating_project(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(CommercialSiteError):
                generate_commercial_site(
                    directory, "too-long",
                    self.brief(facts=[("Information détaillée numéro " + str(i) + " ") * 7 for i in range(8)]),
                )
            self.assertFalse((Path(directory) / "too-long").exists())

    def test_preserves_generator_safety_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                generate_commercial_site(
                    directory, "unsafe", self.brief(facts=["Résultat garanti"])
                )
            self.assertFalse((Path(directory) / "unsafe").exists())

    def test_does_not_overwrite_existing_project(self):
        with tempfile.TemporaryDirectory() as directory:
            generate_commercial_site(directory, "existing", self.brief())
            with self.assertRaises(ValueError):
                generate_commercial_site(directory, "existing", self.brief())

    def test_pharmacy_dosage_is_rejected_before_site_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                generate_commercial_site(
                    directory, "pharmacy",
                    self.brief(sector="pharmacy", facts=["Format 250 mg"]),
                )
            self.assertFalse((Path(directory) / "pharmacy").exists())


if __name__ == "__main__":
    unittest.main()
