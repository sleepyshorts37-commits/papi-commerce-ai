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
            self.assertTrue(report["passed"], report["checks"])
            self.assertTrue(report["checks"]["sector_design_tokens"])
            self.assertIn("--ink: #26364a", (root / "styles.css").read_text())
            self.assertIn("hero--hospitality", (root / "index.html").read_text())


    def test_custom_sections_replace_generic_feature_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = {
                "name": "Portail institutionnel",
                "industry": "education",
                "sections": {
                    "home": [
                        {"id": "programmes", "type": "feature_grid", "eyebrow": "Programmes", "heading": "Nos parcours", "body": "Des formations adaptées.", "items": [
                            {"title": "Débutant", "body": "Les fondamentaux."},
                            {"title": "Avancé", "body": "Approfondir ses compétences."},
                        ]},
                        {"id": "faq", "type": "faq", "eyebrow": "Aide", "heading": "Questions fréquentes", "body": "Tout savoir.", "items": [
                            {"question": "Quand commencer ?", "answer": "À tout moment."},
                        ]},
                    ]
                },
            }
            generate_multi_page_project(tmp, "custom", spec, self.brief())
            page = (Path(tmp) / "custom/index.html").read_text()
            self.assertIn("Nos parcours", page)
            self.assertIn("Questions fréquentes", page)
            self.assertNotIn("Une expérience conçue avec intention.", page)\n            services = (Path(tmp) / "custom/services/index.html").read_text()\n            self.assertIn("Un parcours adapté", services)

    def test_escapes_content_and_marks_current_navigation(self):
        with tempfile.TemporaryDirectory() as tmp:
            brief = self.brief()
            brief["pages"][1]["title"] = '<img src=x onerror=alert(1)>'
            generate_multi_page_project(tmp, "safe", {"name": "Portail institutionnel"}, brief)
            page = (Path(tmp) / "safe/services/index.html").read_text()
            self.assertNotIn("<img", page)
            self.assertIn("&lt;img", page)
            self.assertIn('aria-current="page"', page)

    def test_all_sector_profiles_have_distinct_brand_tokens(self):
        self.assertEqual(len(SECTOR_DESIGNS), 6)
        self.assertEqual(len({item["primary"] for item in SECTOR_DESIGNS.values()}), 6)

    def test_rejects_unsupported_sector(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                generate_multi_page_project(tmp, "bad", {"name": "Portail institutionnel", "industry": "unknown"}, self.brief())

    def test_rejects_name_mismatch_and_duplicate_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                generate_multi_page_project(tmp, "portail", {"name": "Autre"}, self.brief())
            generate_multi_page_project(tmp, "portail", {"name": "Portail institutionnel"}, self.brief())
            with self.assertRaises(ValueError):
                generate_multi_page_project(tmp, "portail", {"name": "Portail institutionnel"}, self.brief())


if __name__ == "__main__":
    unittest.main()
