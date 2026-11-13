import json
import tempfile
import unittest
from pathlib import Path

from papi_core.multipage_site import MultiPageSiteError, generate_multipage_site


class MultiPageSiteTests(unittest.TestCase):
    def brief(self, **updates):
        value = {
            "brand": "Hôtel Baobab",
            "sector": "hotel",
            "audience": "voyageurs",
            "tone": "professional",
            "cta": "Contactez la réception pour confirmer les disponibilités.",
            "pages": [
                {"slug": "accueil", "title": "Bienvenue", "summary": "Présentation de l'hôtel à Saly.",
                 "facts": ["Établissement situé à Saly"]},
                {"slug": "chambres", "title": "Nos chambres", "summary": "Présentation des chambres.",
                 "facts": ["Chambres climatisées", "Wi-Fi disponible"]},
                {"slug": "restaurant", "title": "Restaurant", "summary": "Notre espace de restauration.",
                 "facts": ["Restaurant sur place"]},
            ],
        }
        value.update(updates)
        return value

    def test_creates_pages_navigation_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            result = generate_multipage_site(directory, "hotel-baobab", self.brief())
            root = Path(directory) / "hotel-baobab"
            self.assertEqual(result["page_count"], 3)
            self.assertTrue((root / "index.html").is_file())
            self.assertTrue((root / "pages" / "chambres.html").is_file())
            self.assertIn('href="pages/chambres.html"', (root / "index.html").read_text())
            self.assertIn('href="../index.html"', (root / "pages" / "chambres.html").read_text())
            manifest = json.loads((root / "project.json").read_text())
            self.assertEqual(manifest["engine"], "deterministic-multipage-v1")
            self.assertTrue(result["review_required"])
            self.assertFalse(result["published"])
            self.assertFalse(result["network_used"])

    def test_rejects_duplicate_or_traversal_page_slugs(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = self.brief()["pages"]
            pages[1]["slug"] = "../escape"
            with self.assertRaises(MultiPageSiteError):
                generate_multipage_site(directory, "invalid-site", self.brief(pages=pages))
            self.assertFalse((Path(directory) / "invalid-site").exists())

    def test_rejects_duplicate_page_identifiers(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = self.brief()["pages"]
            pages[1]["slug"] = pages[0]["slug"]
            with self.assertRaises(MultiPageSiteError):
                generate_multipage_site(directory, "duplicate-site", self.brief(pages=pages))

    def test_rejects_unverified_claims_and_pharmacy_dosages(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = self.brief()["pages"]
            pages[0]["facts"] = ["Résultat garanti"]
            with self.assertRaises(ValueError):
                generate_multipage_site(directory, "unsafe-site", self.brief(pages=pages))
            pharmacy_pages = [
                {"slug": "accueil", "title": "Accueil", "summary": "Présentation.",
                 "facts": ["Pharmacie de quartier"]},
                {"slug": "conseils", "title": "Conseils", "summary": "Informations.",
                 "facts": ["Dosage 500 mg"]},
            ]
            with self.assertRaises(ValueError):
                generate_multipage_site(directory, "pharmacy-site",
                    self.brief(sector="pharmacy", pages=pharmacy_pages))
            self.assertFalse((Path(directory) / "unsafe-site").exists())
            self.assertFalse((Path(directory) / "pharmacy-site").exists())

    def test_validates_summary_claims_too(self):
        with tempfile.TemporaryDirectory() as directory:
            pages = self.brief()["pages"]
            pages[0]["summary"] = "Résultat garanti pour tous"
            with self.assertRaises(ValueError):
                generate_multipage_site(directory, "claim-site", self.brief(pages=pages))
            self.assertFalse((Path(directory) / "claim-site").exists())

    def test_refuses_existing_project(self):
        with tempfile.TemporaryDirectory() as directory:
            generate_multipage_site(directory, "existing-site", self.brief())
            with self.assertRaises(MultiPageSiteError):
                generate_multipage_site(directory, "existing-site", self.brief())

    def test_page_count_and_field_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(MultiPageSiteError):
                generate_multipage_site(directory, "one-page", self.brief(pages=self.brief()["pages"][:1]))
            with self.assertRaises(MultiPageSiteError):
                generate_multipage_site(directory, "bad-summary",
                    self.brief(pages=[dict(self.brief()["pages"][0], summary=""), self.brief()["pages"][1]]))


if __name__ == "__main__":
    unittest.main()
