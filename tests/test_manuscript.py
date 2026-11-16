"""Tests de validation et d'assemblage des manuscrits PAPI KIDS."""
import unittest

from papi_core.manuscript import (
    ManuscriptError, render_manuscript_markdown, validate_manuscript,
)


def sample():
    return {
        "title": "Mina et la rivière lumineuse",
        "language": "fr",
        "age_range": "6-9",
        "synopsis": "Mina découvre une rivière qui brille la nuit et apprend à protéger la forêt.",
        "chapters": [
            {
                "title": "La lumière dans les roseaux",
                "text": ("Mina avançait doucement près de la rivière. Les petites lumières "
                         "dansaient sur l'eau et semblaient lui montrer un chemin secret. "
                         "Elle décida de suivre leur éclat avec prudence."),
                "illustration_brief": "Mina observe la rivière au clair de lune.",
            }
        ],
    }


class ManuscriptTests(unittest.TestCase):
    def test_valid_manuscript_has_hash_and_counts(self):
        report = validate_manuscript(sample())
        self.assertEqual(report.chapter_count, 1)
        self.assertGreater(report.word_count, 20)
        self.assertEqual(len(report.content_sha256), 64)

    def test_renderer_assembles_chapters_and_illustration_briefs(self):
        output = render_manuscript_markdown(sample())
        self.assertIn("# Mina et la rivière lumineuse", output)
        self.assertIn("## 1. La lumière dans les roseaux", output)
        self.assertIn("Brief illustration", output)

    def test_empty_chapter_is_rejected(self):
        data = sample()
        data["chapters"][0]["text"] = " "
        with self.assertRaises(ManuscriptError):
            validate_manuscript(data)

    def test_placeholder_is_rejected(self):
        data = sample()
        data["chapters"][0]["text"] += " TODO"
        with self.assertRaises(ManuscriptError):
            validate_manuscript(data)

    def test_invalid_age_range_is_rejected(self):
        data = sample()
        data["age_range"] = "9-6"
        with self.assertRaises(ManuscriptError):
            validate_manuscript(data)

    def test_short_chapter_generates_warning_not_false_approval(self):
        data = sample()
        data["chapters"][0]["text"] = "Mina regarde la rivière."
        report = validate_manuscript(data)
        self.assertTrue(report.warnings)


if __name__ == "__main__":
    unittest.main()
