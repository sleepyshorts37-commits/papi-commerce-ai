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
