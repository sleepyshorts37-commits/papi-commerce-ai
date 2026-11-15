import unittest

from papi_core.papi_kids_mobile_dashboard import render_papi_kids_mobile_dashboard


def scenes():
    return [
        {"page_number": i, "heading": f"Scène {i}",
         "detail": "En attente de production",
         "status": "pending_visual_review"}
        for i in range(1, 25)
    ]


class PapiKidsMobileDashboardTests(unittest.TestCase):
    def test_renders_responsive_dashboard_and_24_pages(self):
        html = render_papi_kids_mobile_dashboard(
            book_id="PKP-0001", title="Nia et la rivière",
            page_count=24, scenes=scenes())
        self.assertIn('name="viewport"', html)
        self.assertIn('data-filter="pending_visual_review"', html)
        self.assertEqual(html.count('class="scene"'), 24)
        self.assertIn("jeton Bearer", html)
        self.assertIn("Consulter l'état d'un manuscrit", html)
        self.assertIn("/api/papi-kids/manuscripts/", html)
        self.assertIn("statusResult.textContent", html)
        self.assertIn("Jeton de validation humaine", html)
        self.assertIn("Approuver", html)
        self.assertIn("sourceWidth", html)
        self.assertIn("super-résolution à vérifier", html)
        self.assertIn("/review", html)
        self.assertIn("replaceChildren", html)
        self.assertIn("Mes livres", html)
        self.assertIn("/api/papi-kids/manuscripts", html)
        self.assertIn("Actualiser ma bibliothèque", html)
        self.assertIn("Validation de sécurité jeunesse", html)
        self.assertIn("Jeton distinct de revue sécurité", html)
        self.assertIn("/safety-review", html)
        self.assertIn("renderSafetyReview", html)
        self.assertIn("manuscript_sha256", html)
        self.assertIn("Valider la sécurité", html)
        self.assertIn("Fiche commerciale Amazon KDP", html)
        self.assertIn("Jeton distinct des métadonnées KDP", html)
        self.assertIn("/kdp-metadata", html)
        self.assertIn("readKdpMetadataForm", html)
        self.assertIn("categories", html)
        self.assertIn("isbn_strategy", html)
        self.assertIn("kdp_listing_metadata_blockers", html)
        self.assertIn("metadataTokenInput.value=\"\"", html)
        self.assertIn("Fabrication du package KDP", html)
        self.assertIn("Jeton distinct de fabrication KDP", html)
        self.assertIn("/build-kdp-package", html)
        self.assertIn("window.confirm", html)
        self.assertIn("publication ne sera effectuée", html)
        self.assertIn("packageBuild.status", html)
        self.assertIn("État de l'infrastructure", html)
        self.assertIn("/api/papi-kids/readiness", html)
        self.assertIn("Aucun secret affiché", html)
        self.assertIn("readinessTokenInput.value=\"\"", html)
        self.assertIn("Inspection humaine des fichiers KDP", html)
        self.assertIn("/kdp-package/", html)
        self.assertIn("/kdp-package-review", html)
        self.assertIn("openKdpPackageArtifact", html)
        self.assertIn("submitKdpPackageReview", html)
        self.assertIn("kdp_package_reviews", html)
        self.assertIn("Validation Kindle Previewer", html)
        self.assertIn("/kindle-previewer-review", html)
        self.assertIn("submitKindlePreviewerReview", html)
        self.assertIn("kindle_previewer_review", html)

    def test_escapes_user_content(self):
        html = render_papi_kids_mobile_dashboard(
            book_id="PKP-0001", title="<script>alert(1)</script>",
            page_count=24, scenes=scenes())
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_rejects_missing_or_misordered_scenes(self):
        data = scenes()
        data[1]["page_number"] = 1
        with self.assertRaises(ValueError):
            render_papi_kids_mobile_dashboard(
                book_id="PKP-0001", title="Nia", page_count=24, scenes=data)

    def test_rejects_unknown_status(self):
        data = scenes()
        data[0]["status"] = "published"
        with self.assertRaises(ValueError):
            render_papi_kids_mobile_dashboard(
                book_id="PKP-0001", title="Nia", page_count=24, scenes=data)


if __name__ == "__main__":
    unittest.main()
