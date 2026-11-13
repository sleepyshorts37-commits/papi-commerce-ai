import unittest

from papi_core.site_architecture import SiteArchitectureError, build_site_architecture


class SiteArchitectureTests(unittest.TestCase):
    def brief(self):
        return {
            "project_name": "Site de démonstration",
            "requirements": [
                {"id": "brand", "description": "Présenter la marque", "priority": "must"},
                {"id": "contact", "description": "Contacter l'équipe", "priority": "should"},
            ],
            "pages": [
                {"slug": "home", "title": "Accueil", "purpose": "Découvrir le site", "requirements": ["brand"]},
                {"slug": "contact", "title": "Contact", "purpose": "Joindre l'équipe", "requirements": ["contact"]},
            ],
        }

    def test_builds_sitemap_and_traceability(self):
        result = build_site_architecture(self.brief())
        self.assertEqual(result["status"], "architecture_validated_not_generated")
        self.assertEqual(result["traceability"], {"brand": ["home"], "contact": ["contact"]})
        self.assertEqual(result["pages"][1]["file"], "contact/index.html")

    def test_requires_home_page(self):
        brief = self.brief()
        brief["pages"].pop(0)
        with self.assertRaises(SiteArchitectureError):
            build_site_architecture(brief)

    def test_rejects_uncovered_requirement(self):
        brief = self.brief()
        brief["requirements"].append({"id": "pricing", "description": "Présenter les tarifs", "priority": "could"})
        with self.assertRaises(SiteArchitectureError):
            build_site_architecture(brief)

    def test_rejects_duplicate_page_slug(self):
        brief = self.brief()
        brief["pages"].append(dict(brief["pages"][0]))
        with self.assertRaises(SiteArchitectureError):
            build_site_architecture(brief)


if __name__ == "__main__":
    unittest.main()
