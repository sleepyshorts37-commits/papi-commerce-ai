import hashlib
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from PIL import Image
import reportlab

from papi_core.papi_kids_fixed_layout_epub import (
    KDPFixedLayoutEPUBError,
    build_kdp_fixed_layout_epub,
)


def asset(root, key, page_number=None):
    path = Path(root) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (9, 9), (150, 160, 170)).save(path, format="PNG")
    data = path.read_bytes()
    result = {
        "storage_key": key, "sha256": hashlib.sha256(data).hexdigest(),
        "media_type": "image/png", "width_px": 9, "height_px": 9,
        "review_status": "approved",
    }
    if page_number is not None:
        result["page_number"] = page_number
    return result


class PapiKidsFixedLayoutEPUBTests(unittest.TestCase):
    def test_builds_epub3_with_text_popups_and_single_page_xhtml(self):
        with tempfile.TemporaryDirectory() as root:
            upload_id = "PKP-UP-" + "a" * 32
            cover = asset(root, "covers/ebook-cover.png")
            images = [asset(root, f"{upload_id}/illustrations/page-{n:02d}.png", n)
                      for n in range(1, 25)]
            pages = [{
                "page_number": n, "text": f"Nia observe la rivière, page {n}.",
                "text_box": {"x": 8, "y": 8, "width": 75, "height": 20},
            } for n in range(1, 25)]
            font = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
            output = Path(root) / "book.epub"
            result = build_kdp_fixed_layout_epub(
                root, output, upload_id=upload_id,
                title="Nia et la rivière aux mille reflets",
                author="Auteur confirmé", language="fr",
                identifier="urn:papi:PKP-0001", modified_at="2026-11-15T22:00:00Z",
                pages=pages, page_assets=images, cover_asset=cover,
                canvas_width_px=9, canvas_height_px=9, font_path=font,
            )
            self.assertTrue(output.exists())
            self.assertEqual(result["page_count"], 24)
            self.assertTrue(result["text_popups"])
            with ZipFile(output) as archive:
                self.assertEqual(archive.namelist()[0], "mimetype")
                self.assertIn(b"pre-paginated", archive.read("OEBPS/package.opf"))
                self.assertIn(b"app-amzn-magnify", archive.read("OEBPS/pages/page-001.xhtml"))
                self.assertEqual(archive.testzip(), None)

    def test_rejects_unapproved_page_art(self):
        with tempfile.TemporaryDirectory() as root:
            upload_id = "PKP-UP-" + "b" * 32
            cover = asset(root, "covers/ebook-cover.png")
            images = [asset(root, f"{upload_id}/illustrations/page-{n:02d}.png", n)
                      for n in range(1, 25)]
            images[0]["review_status"] = "pending_review"
            pages = [{"page_number": n, "text": "Nia.", "text_box": {
                "x": 8, "y": 8, "width": 75, "height": 20,
            }} for n in range(1, 25)]
            with self.assertRaises(KDPFixedLayoutEPUBError):
                build_kdp_fixed_layout_epub(
                    root, Path(root) / "book.epub", upload_id=upload_id,
                    title="Nia", author="Auteur", language="fr", identifier="urn:papi:1",
                    modified_at="2026-11-15T22:00:00Z", pages=pages, page_assets=images,
                    cover_asset=cover, canvas_width_px=9, canvas_height_px=9,
                    font_path=Path(reportlab.__file__).parent / "fonts" / "Vera.ttf",
                )

    def test_rejects_text_popups_near_screen_edges(self):
        with tempfile.TemporaryDirectory() as root:
            upload_id = "PKP-UP-" + "c" * 32
            cover = asset(root, "covers/ebook-cover.png")
            images = [asset(root, f"{upload_id}/illustrations/page-{n:02d}.png", n)
                      for n in range(1, 25)]
            pages = [{"page_number": n, "text": "Nia.", "text_box": {
                "x": 1, "y": 8, "width": 95, "height": 20,
            }} for n in range(1, 25)]
            with self.assertRaises(KDPFixedLayoutEPUBError):
                build_kdp_fixed_layout_epub(
                    root, Path(root) / "book.epub", upload_id=upload_id,
                    title="Nia", author="Auteur", language="fr", identifier="urn:papi:1",
                    modified_at="2026-11-15T22:00:00Z", pages=pages, page_assets=images,
                    cover_asset=cover, canvas_width_px=9, canvas_height_px=9,
                    font_path=Path(reportlab.__file__).parent / "fonts" / "Vera.ttf",
                )


if __name__ == "__main__":
    unittest.main()
