import tempfile
import unittest
from pathlib import Path

from papi_core.multi_page_builder import SECTOR_DESIGNS, generate_multi_page_project, multi_page_quality_report


class MultiPageBuilderTests(unittest.TestCase):
    def brief(self):
        return {
            "project_name": "Portail institutionnel",
            "requirements": [
                {"id": "brand", "description": "Présenter la marque", "priority": "must"},
                {"id": "services", "description": "Présenter les services", "priority": "must"},
                {"id": "contact", "description": "Contacter l'équipe", "priority": "must"},
            ],
            "pages": [
                {"slug": "home", "title": "Accueil", "purpose": "Découvrir l'organisation", "requirements": ["brand"]},
                {"slug": "services", "title": "Services", "purpose": "Découvrir les offres", "requirements": ["services"]},
                {"slug": "contact", "title": "Contact", "purpose": "Joindre l'équipe", "requirements": ["contact"]},
            ],
        }

    def test_generates_linked_three_page_site_and_sitemap(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = generate_multi_page_project(tmp, "portail", {"name": "Portail institutionnel", "industry": "hospitality"}, self.brief())
            root = Path(tmp) / "portail"
            self.assertEqual(result["page_count"], 3)
            self.assertTrue((root / "index.html").is_file())
            self.assertTrue((root / "services/index.html").is_file())
            self.assertTrue((root / "contact/index.html").is_file())
            self.assertTrue((root / "sitemap.xml").is_file())
            report = multi_page_quality_report(tmp, "portail")
            self.assertTrue(report["passed"], report["checks"])\n            self.assertEqual(report["checks"]["sector_design_tokens"], True)\n            self.assertIn("--ink: #26364a", (root / "styles.css").read_text())\n            self.assertIn("hero--hospitality", (root / "index.html").read_text())

    def test_escapes_content_and_marks_current_navigation(self):
        with tempfile.TemporaryDirectory() as tmp:
            brief = self.brief()
            brief["pages"][1]["title"] = '<img src=x onerror=alert(1)>'
            generate_multi_page_project(tmp, "safe", {"name": "Portail institutionnel"}, brief)
            page = (Path(tmp) / "safe/services/index.html").read_text()
            self.assertNotIn("<img", page)
            self.assertIn("&lt;img", page)
            self.assertIn('aria-current="page"', page)

    def test_all_sector_profiles_have_distinct_brand_tokens(self):\n        self.assertEqual(len(SECTOR_DESIGNS), 6)\n        self.assertEqual(len({item["primary"] for item in SECTOR_DESIGNS.values()}), 6)\n\n    def test_rejects_unsupported_sector(self):\n        with tempfile.TemporaryDirectory() as tmp:\n            with self.assertRaises(ValueError):\n                generate_multi_page_project(tmp, "bad", {"name": "Portail institutionnel", "industry": "unknown"}, self.brief())\n\n    def test_rejects_name_mismatch_and_duplicate_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                generate_multi_page_project(tmp, "portail", {"name": "Autre"}, self.brief())
            generate_multi_page_project(tmp, "portail", {"name": "Portail institutionnel", "industry": "corporate"}, self.brief())
            with self.assertRaises(ValueError):
                generate_multi_page_project(tmp, "portail", {"name": "Portail institutionnel"}, self.brief())


if __name__ == "__main__":
    unittest.main()
