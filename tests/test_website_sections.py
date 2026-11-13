import unittest

from papi_core.website_sections import WebsiteSectionError, render_page_sections


class WebsiteSectionTests(unittest.TestCase):
    def test_renders_safe_feature_stats_faq_and_internal_cta(self):
        sections = [
            {"id": "features", "type": "feature_grid", "eyebrow": "Atouts", "heading": "Nos services", "body": "Une offre claire.", "items": [
                {"title": "Conseil", "body": "Une expertise adaptée."},
                {"title": "Suivi", "body": "Un accompagnement continu."},
            ]},
            {"id": "numbers", "type": "stats", "eyebrow": "Repères", "heading": "Quelques chiffres", "body": "Nos indicateurs.", "items": [
                {"value": "24/7", "label": "Disponibilité"},
                {"value": "98 %", "label": "Satisfaction"},
            ]},
            {"id": "answers", "type": "faq", "eyebrow": "FAQ", "heading": "Questions fréquentes", "body": "Informations utiles.", "items": [
                {"question": "Comment démarrer ?", "answer": "Contactez notre équipe."},
            ]},
            {"id": "next", "type": "cta", "eyebrow": "Contact", "heading": "Parlons-en", "body": "Échangeons.", "cta_label": "Nous contacter", "target_page": "contact"},
        ]
        html = render_page_sections(sections, "home", {"home", "contact"})
        self.assertIn('class="feature-grid"', html)
        self.assertIn('class="stats-grid"', html)
        self.assertIn("<details>", html)
        self.assertIn('href="contact/index.html"', html)

    def test_escapes_user_content_and_routes_from_nested_page(self):
        section = [{"id": "intro", "type": "intro", "eyebrow": "À propos", "heading": '<script>alert(1)</script>', "body": "Texte"}]
        html = render_page_sections(section, "services", {"home", "services"})
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

        cta = [{"id": "go-home", "type": "cta", "eyebrow": "Retour", "heading": "Accueil", "body": "Retourner.", "cta_label": "Voir l'accueil", "target_page": "home"}]
        rendered = render_page_sections(cta, "services", {"home", "services"})
        self.assertIn('href="../index.html"', rendered)

    def test_rejects_unknown_target_and_untrusted_fields(self):
        with self.assertRaises(WebsiteSectionError):
            render_page_sections([{"id": "go", "type": "cta", "eyebrow": "x", "heading": "x", "body": "x", "cta_label": "x", "target_page": "https://evil.test"}], "home", {"home"})
        with self.assertRaises(WebsiteSectionError):
            render_page_sections([{"id": "raw", "type": "intro", "eyebrow": "x", "heading": "x", "body": "x", "html": "<script>"}], "home", {"home"})
        with self.assertRaises(WebsiteSectionError):
            render_page_sections([{"id": "x", "type": [], "heading": "x"}], "home", {"home"})

    def test_rejects_duplicate_ids_and_excessive_sections(self):
        section = {"id": "intro", "type": "intro", "eyebrow": "À propos", "heading": "Titre", "body": "Texte"}
        with self.assertRaises(WebsiteSectionError):
            render_page_sections([section, section], "home", {"home"})
        with self.assertRaises(WebsiteSectionError):
            render_page_sections([section] * 9, "home", {"home"})


    def test_renders_business_components_with_provenance_and_internal_product_routes(self):
        sections = [
            {"id": "products", "type": "product_catalog", "eyebrow": "Boutique", "heading": "Nos produits", "body": "Sélection.", "items": [
                {"name": "Café", "description": "Café local.", "price_label": "3 000 FCFA", "cta_label": "Détails", "target_page": "contact"},
            ]},
            {"id": "team", "type": "team", "eyebrow": "Équipe", "heading": "Notre équipe", "body": "", "items": [
                {"name": "Awa", "role": "Conseillère", "bio": "Accompagne les clients."},
            ]},
            {"id": "reviews", "type": "testimonials", "eyebrow": "Avis", "heading": "Ils en parlent", "body": "", "items": [
                {"quote": "Service apprécié.", "author": "Client A", "role": "Client"},
            ]},
            {"id": "services", "type": "service_cards", "eyebrow": "Offres", "heading": "Nos services", "body": "", "items": [
                {"title": "Livraison", "body": "Livraison sur demande."},
            ]},
        ]
        rendered = render_page_sections(sections, "home", {"home", "contact"})
        self.assertIn('href="contact/index.html"', rendered)
        self.assertIn("Café", rendered)
        self.assertIn("Awa", rendered)
        self.assertIn("authenticité n’a pas été vérifiée", rendered)
        self.assertIn("service-card", rendered)

    def test_rejects_external_product_target_and_extra_team_fields(self):
        with self.assertRaises(WebsiteSectionError):
            render_page_sections([{"id": "products", "type": "product_catalog", "eyebrow": "x", "heading": "x", "body": "", "items": [
                {"name": "Item", "description": "Texte", "price_label": "1 XOF", "cta_label": "Acheter", "target_page": "https://example.com"},
            ]}], "home", {"home"})
        with self.assertRaises(WebsiteSectionError):
            render_page_sections([{"id": "team", "type": "team", "eyebrow": "x", "heading": "x", "body": "", "items": [
                {"name": "Awa", "role": "CEO", "bio": "Bio", "photo_url": "https://example.com/a.jpg"},
            ]}], "home", {"home"})


if __name__ == "__main__":
    unittest.main()
