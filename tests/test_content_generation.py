import unittest
from papi_core.content_generation import ContentGenerationError, generate_commercial_content

class ContentGenerationTests(unittest.TestCase):
    def brief(self, **updates):
        value = {"content_type":"product","sector":"retail","brand":"Boutique Baobab",
                 "offer":"Sac artisanal","audience":"clientèle locale",
                 "facts":["Fabrication artisanale","Disponible en plusieurs coloris"],
                 "tone":"professional","cta":"Écrivez-nous pour connaître les disponibilités."}
        value.update(updates)
        return value

    def test_uses_only_supplied_facts(self):
        result = generate_commercial_content(self.brief())
        self.assertIn("Fabrication artisanale", result["body"])
        self.assertNotIn("livraison gratuite", result["body"])
        self.assertEqual(result["review_required"], "true")

    def test_all_types_and_sectors(self):
        for kind in ("product","service","business_page","social_post"):
            for sector in ("pharmacy","hotel","restaurant","retail","professional_services"):
                result = generate_commercial_content(self.brief(content_type=kind, sector=sector))
                self.assertEqual((result["content_type"], result["sector"]), (kind, sector))

    def test_pharmacy_notice_and_dosage_block(self):
        result = generate_commercial_content(self.brief(sector="pharmacy"))
        self.assertIn("professionnel de santé", result["disclaimer"])
        with self.assertRaises(ContentGenerationError):
            generate_commercial_content(self.brief(sector="pharmacy", facts=["Dosage 500 mg"]))

    def test_blocks_unverified_claims(self):
        for claim in ("Guérit rapidement", "Résultat garanti", "100% efficace"):
            with self.subTest(claim=claim), self.assertRaises(ContentGenerationError):
                generate_commercial_content(self.brief(facts=[claim]))

    def test_rejects_unknown_or_unsupported_values(self):
        for changes in ({"unapproved_claim":"oui"},{"sector":"casino"},{"content_type":"email_blast"}):
            with self.subTest(changes=changes), self.assertRaises(ContentGenerationError):
                generate_commercial_content(self.brief(**changes))

    def test_rejects_non_text_selectors_without_type_error(self):
        for changes in ({"sector": []}, {"content_type": {}}, {"tone": []}):
            with self.subTest(changes=changes), self.assertRaises(ContentGenerationError):
                generate_commercial_content(self.brief(**changes))

    def test_rejects_bad_facts(self):
        for facts in ([], ["x"*181], ["<script>alert(1)</script>"], [f"Fait {i}" for i in range(9)]):
            with self.subTest(facts=facts), self.assertRaises(ContentGenerationError):
                generate_commercial_content(self.brief(facts=facts))

if __name__ == "__main__":
    unittest.main()
