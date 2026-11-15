import tempfile
import unittest
from pathlib import Path
import base64
import reportlab

from papi_core.papi_kids_kdp_preflight import (
    KDPPreflightError,
    build_interior_pdf,
    calculate_kdp_cover_dimensions,
    validate_kdp_spec,
)

# Valid 1x1 PNG fixture. Tests lower dpi_target to 1; production defaults to 300.
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/"
    "q9sAAAAASUVORK5CYII="
)


class PapiKidsKDPPreflightTests(unittest.TestCase):
    def test_24_page_album_requires_premium_color_not_standard_color(self):
        with self.assertRaises(KDPPreflightError):
            validate_kdp_spec(
                trim_width_in=8.5, trim_height_in=8.5, page_count=24,
                color_mode="standard_color", bleed=True,
                inside_margin_in=.375, outside_margin_in=.375,
                top_margin_in=.375, bottom_margin_in=.375,
            )
        result = validate_kdp_spec(
            trim_width_in=8.5, trim_height_in=8.5, page_count=24,
            color_mode="premium_color", bleed=True,
            inside_margin_in=.375, outside_margin_in=.375,
            top_margin_in=.375, bottom_margin_in=.375,
        )
        self.assertEqual(result["pdf_width_in"], 8.625)
        self.assertEqual(result["pdf_height_in"], 8.75)

    def test_cover_spine_and_bleed_calculation(self):
        result = calculate_kdp_cover_dimensions(
            trim_width_in=8.5, trim_height_in=8.5, page_count=24,
        )
        self.assertAlmostEqual(result["spine_width_in"], .056328)
        self.assertAlmostEqual(result["cover_width_in"], 17.306328)
        self.assertFalse(result["spine_text_allowed"])
        self.assertTrue(result["template_required_before_export"])

    def test_margin_and_page_limit_failures(self):
        with self.assertRaises(KDPPreflightError):
            validate_kdp_spec(
                trim_width_in=8.5, trim_height_in=8.5, page_count=24,
                color_mode="premium_color", bleed=False,
                inside_margin_in=.2, outside_margin_in=.25,
                top_margin_in=.25, bottom_margin_in=.25,
            )

    def test_builds_24_page_pdf_from_approved_assets_only(self):
        with tempfile.TemporaryDirectory() as root:
            upload_id = "PKP-UP-" + "a" * 32
            book_dir = Path(root) / upload_id / "illustrations"
            book_dir.mkdir(parents=True)
            assets = []
            pages = []
            for number in range(1, 25):
                name = f"page-{number:02d}-v001.png"
                (book_dir / name).write_bytes(PNG_1PX)
                import hashlib
                assets.append({
                    "page_number": number, "version": 1, "review_status": "approved",
                    "storage_key": f"{upload_id}/illustrations/{name}",
                    "media_type": "image/png", "width_px": 1, "height_px": 1,
                    "sha256": hashlib.sha256(PNG_1PX).hexdigest(),
                })
                pages.append({
                    "page_number": number, "text": f"Page {number}",
                    "text_box": {"x": .5, "y": .5, "width": 7.5, "height": 7.5},
                })
            font_path = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
            output = Path(root) / "interior.pdf"
            result = build_interior_pdf(
                root, output, upload_id=upload_id, assets=assets, pages=pages,
                font_path=font_path, trim_width_in=8.5, trim_height_in=8.5,
                color_mode="premium_color", bleed=False,
                inside_margin_in=.375, outside_margin_in=.25,
                top_margin_in=.25, bottom_margin_in=.25, dpi_target=1,
            )
            self.assertTrue(output.read_bytes().startswith(b"%PDF-"))
            self.assertEqual(result["page_count"], 24)
            self.assertTrue(result["font_embedded"])
            self.assertFalse(result["kdp_submission_ready"])

    def test_pdf_refuses_unapproved_image(self):
        with tempfile.TemporaryDirectory() as root:
            upload_id = "PKP-UP-" + "a" * 32
            book_dir = Path(root) / upload_id / "illustrations"
            book_dir.mkdir(parents=True)
            for number in range(1, 25):
                name = f"page-{number:02d}-v001.png"
                (book_dir / name).write_bytes(PNG_1PX)
            assets = [{
                "page_number": number, "review_status": "pending_review",
                "storage_key": f"{upload_id}/illustrations/page-{number:02d}-v001.png",
            } for number in range(1, 25)]
            pages = [{
                "page_number": number, "text": "Texte",
                "text_box": {"x": .5, "y": .5, "width": 7.5, "height": 7.5},
            } for number in range(1, 25)]
            font_path = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
            with self.assertRaises(KDPPreflightError):
                build_interior_pdf(
                    root, Path(root) / "refused.pdf", upload_id=upload_id,
                    assets=assets, pages=pages, font_path=font_path,
                    trim_width_in=8.5, trim_height_in=8.5,
                    color_mode="premium_color", bleed=False,
                    inside_margin_in=.375, outside_margin_in=.25,
                    top_margin_in=.25, bottom_margin_in=.25, dpi_target=1,
                )


if __name__ == "__main__":
    unittest.main()
