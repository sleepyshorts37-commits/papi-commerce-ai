"""Tests du flux d'export de fichiers PAPI KIDS."""
import json
import tempfile
import unittest
from pathlib import Path

from papi_core.export import BookExportError, export_book_files


class BookExportTests(unittest.TestCase):
    def manuscript(self):
        return {
            "title": "Mina et la rivière",
            "language": "fr",
            "age_range": "6-9",
            "synopsis": "Mina découvre une rivière lumineuse.",
            "chapters": [
                {"title": "La découverte", "text": "Mina marche près de la rivière. Elle voit une lumière."}
            ],
        }

    def test_exports_markdown_epub_pdf_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = export_book_files(self.manuscript(), tmp)
            names = {item["name"] for item in result["files"]}
            self.assertIn("mina-et-la-riviere.md", names)
            self.assertIn("mina-et-la-riviere.epub", names)
            self.assertIn("mina-et-la-riviere-interior-proof.pdf", names)
            self.assertFalse(result["illustrations_included"])
            self.assertEqual(result["publication_status"], "not_published")
            manifest_path = Path(tmp) / "mina-et-la-riviere-manifest.json"
            self.assertTrue(manifest_path.exists())
            json.loads(manifest_path.read_text(encoding="utf-8"))

    def test_export_refuses_to_overwrite_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            export_book_files(self.manuscript(), tmp)
            with self.assertRaises(BookExportError):
                export_book_files(self.manuscript(), tmp)

    def test_invalid_manuscript_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = self.manuscript()
            data["chapters"] = []
            with self.assertRaises(ValueError):
                export_book_files(data, tmp)


if __name__ == "__main__":
    unittest.main()
