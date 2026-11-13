import unittest

from papi_core.site_architecture import (
    SiteArchitectureError,
    build_site_architecture,
)


class SiteArchitectureTests(unittest.TestCase):
    def brief(self):
        return {
            "project_name": "Portail institutionnel",
            "requirements": [
                {"id": "brand", "description": "Présenter la marque", "priority": "must"},
                {"id": "contact", "description": "Permettre le contact", "priority": "must"},
                {"id": "services", "description": "Présenter les services", "priority": "should"},
            ],
            "pages": [
                {"slug": "home", "title": "Accueil", "purpose": "Découvrir l'organisation", "requirements": ["brand"]},
                {"slug": "services", "title": "Nos services", "purpose": "Comprendre les offres", "requirements": ["services"]},
                {"slug": "contact", "title": "Contact", "purpose": "Contacter l'équipe", "requirements": ["contact"]},
            ],
        }

    def test_builds_sitemap_and_traceability(self):
        result = build_site_architecture(self.brief())
        self.assertEqual(result["status"], "architecture_validated_not_generated")
        self.assertEqual([page["route"] for page in result["pages"]], ["/", "/services/", "/contact/"])
        self.assertEqual(result["traceability"]["contact"], ["contact"])
        self.assertEqual(result["pages"][1]["file"], "services/index.html")

    def test_requires_home_page(self):
        brief = self.brief()
        brief["pages"] = brief["pages"][1:]
        with self.assertRaises(SiteArchitectureError):
            build_site_architecture(brief)

    def test_rejects_duplicate_routes(self):
        brief = self.brief()
        brief["pages"].append(dict(brief["pages"][1]))
        with self.assertRaises(SiteArchitectureError):
            build_site_architecture(brief)

    def test_rejects_unknown_requirement_reference(self):
        brief = self.brief()
        brief["pages"][0]["requirements"] = ["missing"]
        with self.assertRaises(SiteArchitectureError):
            build_site_architecture(brief)

    def test_rejects_uncovered_requirement(self):
        brief = self.brief()
        brief["pages"][0]["requirements"] = ["brand"]
        brief["pages"][1]["requirements"] = ["services"]
        brief["pages"][2]["requirements"] = ["contact"]
        brief["requirements"].append(
            {"id": "privacy", "description": "Informer sur la confidentialité", "priority": "must"}
        )
        with self.assertRaises(SiteArchitectureError):
            build_site_architecture(brief)

    def test_rejects_traversal_route(self):
        brief = self.brief()
        brief["pages"][1]["slug"] = "../admin"
        with self.assertRaises(SiteArchitectureError):
            build_site_architecture(brief)

    def test_rejects_duplicate_requirement_ids(self):
        brief = self.brief()
        brief["requirements"].append(dict(brief["requirements"][0]))
        with self.assertRaises(SiteArchitectureError):
            build_site_architecture(brief)


if __name__ == "__main__":
    unittest.main()
