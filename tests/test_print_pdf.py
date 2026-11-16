"""Tests de l'épreuve PDF intérieure PAPI KIDS."""
import unittest

from papi_core.print_pdf import PrintLayout, PrintPdfError, build_print_interior_pdf


class PrintPdfTests(unittest.TestCase):
    def sample(self):
        return {
            "title": "Mina et la rivière",
            "language": "fr",
            "age_range": "6-9",
            "synopsis": "Mina découvre une rivière lumineuse.",
            "chapters": [
                {"title": "La découverte", "text": "Mina marche près de la rivière.\n\nElle voit une lumière."}
            ],
        }

    def test_builds_pdf_with_default_square_trim(self):
        content = build_print_interior_pdf(self.sample())
        self.assertTrue(content.startswith(b"%PDF-"))
        self.assertTrue(content.rstrip().endswith(b"%%EOF"))

    def test_custom_trim_size(self):
        content = build_print_interior_pdf(self.sample(), PrintLayout(width_in=8.0, height_in=10.0))
        self.assertTrue(content.startswith(b"%PDF-"))

    def test_invalid_trim_size_is_rejected(self):
        with self.assertRaises(PrintPdfError):
            build_print_interior_pdf(self.sample(), PrintLayout(width_in=3.0))

    def test_invalid_manuscript_is_rejected(self):
        data = self.sample()
        data["chapters"] = []
        with self.assertRaises(ValueError):
            build_print_interior_pdf(data)


if __name__ == "__main__":
    unittest.main()
