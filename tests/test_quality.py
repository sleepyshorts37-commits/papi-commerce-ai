"""Tests des contrôles éditoriaux déterministes PAPI KIDS."""
import unittest

from papi_core.quality import review_manuscript


def sample():
    return {
        "title": "Mina et la rivière",
        "language": "fr",
        "age_range": "6-9",
        "synopsis": "Mina découvre une rivière lumineuse et apprend à protéger la nature.",
        "chapters": [
            {"title": "La découverte", "text": (
                "Mina marchait près de la rivière lorsque les étoiles apparurent. "
                "Elle entendit un doux murmure et décida de regarder autour d'elle."
            )},
            {"title": "Le retour", "text": (
                "Le lendemain, Mina revint au même endroit avec son amie. "
                "Ensemble, elles ramassèrent les déchets au bord de l'eau."
            )},
        ],
    }


class EditorialQualityTests(unittest.TestCase):
    def test_valid_manuscript_always_requires_human_review(self):
        report = review_manuscript(sample())
        self.assertEqual(report["status"], "requires_human_review")
        self.assertTrue(report["human_review_required"])
        self.assertEqual(report["blockers"], [])
        self.assertEqual(report["metrics"]["chapter_count"], 2)

    def test_invalid_manuscript_is_blocked(self):
        data = sample()
        data["chapters"] = []
        report = review_manuscript(data)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["blockers"][0]["code"], "STRUCTURE_INVALID")

    def test_duplicate_chapter_titles_are_flagged(self):
        data = sample()
        data["chapters"][1]["title"] = data["chapters"][0]["title"]
        report = review_manuscript(data)
        self.assertIn("DUPLICATE_CHAPTER_TITLE", [x["code"] for x in report["warnings"]])

    def test_duplicate_long_paragraphs_are_flagged(self):
        data = sample()
        repeated = "Mina observe attentivement la rivière et promet de protéger les animaux."
        data["chapters"][0]["text"] = repeated
        data["chapters"][1]["text"] = repeated
        report = review_manuscript(data)
        self.assertEqual(report["metrics"]["duplicate_long_paragraphs"], 1)
        self.assertIn("REPEATED_PARAGRAPHS", [x["code"] for x in report["warnings"]])

    def test_report_never_claims_editorial_approval(self):
        report = review_manuscript(sample())
        self.assertTrue(any("revue humaine" in x for x in report["limitations"]))


if __name__ == "__main__":
    unittest.main()
