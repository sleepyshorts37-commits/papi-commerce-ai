"""Tests du générateur EPUB 3 minimal."""
import unittest
import zipfile
import io

from papi_core.epub import EpubError, build_epub, inspect_epub


class EpubTests(unittest.TestCase):
    def manuscript(self):
        return {
            "title": "Mina & la rivière",
            "language": "fr",
            "age_range": "6-9",
            "synopsis": "Mina découvre une rivière lumineuse.",
            "chapters": [
                {"title": "La nuit", "text": "Mina sort dans le jardin.\n\nElle voit la rivière briller.",
                 "illustration_brief": "Une rivière sous les étoiles."}
            ],
        }

    def test_builds_epub3_zip_with_required_files(self):
        content = build_epub(self.manuscript())
        report = inspect_epub(content)
        self.assertTrue(report["valid_archive"])
        self.assertEqual(report["chapters"], 1)
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            self.assertEqual(archive.namelist()[0], "mimetype")
            self.assertIn(b"Mina &amp; la riviÃ¨re", archive.read("EPUB/title.xhtml"))

    def test_invalid_manuscript_is_rejected(self):
        data = self.manuscript()
        data["chapters"] = []
        with self.assertRaises(ValueError):
            build_epub(data)

    def test_corrupt_archive_is_rejected(self):
        with self.assertRaises(EpubError):
            inspect_epub(b"not an epub")


if __name__ == "__main__":
    unittest.main()
