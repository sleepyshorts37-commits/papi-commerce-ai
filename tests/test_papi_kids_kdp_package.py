import hashlib
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
import reportlab
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

from papi_core.papi_kids_kdp_package import KDPPrintPackageError, build_kdp_print_package


def png_chunk(kind, payload):
    return (len(payload).to_bytes(4, "big") + kind + payload +
            (zlib.crc32(kind + payload) & 0xffffffff).to_bytes(4, "big"))


def png_fixture(width=900, height=900):
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    row = b"\x00" + b"\x22\x88\xaa\xff" * width
    return (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", header) +
            png_chunk(b"IDAT", zlib.compress(row * height)) + png_chunk(b"IEND", b""))


class PapiKidsKDPPrintPackageTests(unittest.TestCase):
    def setup_sources(self, root):
        upload = "PKP-UP-" + "d" * 32
        book_dir = Path(root) / upload
        book_dir.mkdir()
        images_dir = book_dir / "illustrations"
        images_dir.mkdir()
        cover_dir = book_dir / "covers"
        cover_dir.mkdir()
        png = png_fixture()
        assets = []
        pages = []
        for number in range(1, 25):
            path = images_dir / f"page-{number:02d}.png"
            path.write_bytes(png)
            assets.append({
                "page_number": number, "review_status": "approved",
                "storage_key": f"{upload}/illustrations/{path.name}",
                "media_type": "image/png", "width_px": 900, "height_px": 900,
                "sha256": hashlib.sha256(png).hexdigest(),
            })
            pages.append({
                "page_number": number, "text": f"Page {number}",
                "text_box": {"x": .5, "y": .5, "width": 7.5, "height": 7.5},
            })
        cover_assets = []
        for name in ("back", "front"):
            path = cover_dir / f"{name}.png"
            path.write_bytes(png)
            cover_assets.append({
                "review_status": "approved",
                "storage_key": f"{upload}/covers/{name}.png",
                "media_type": "image/png", "width_px": 900, "height_px": 900,
                "sha256": hashlib.sha256(png).hexdigest(),
            })
        template = book_dir / "official-template.pdf"
        template_pdf = canvas.Canvas(str(template), pagesize=(17.5 * inch, 8.75 * inch), invariant=1)
        template_pdf.showPage()
        template_pdf.save()
        template_hash = hashlib.sha256(template.read_bytes()).hexdigest()
        layout = {
            "source_template_sha256": template_hash,
            "page_width_in": 17.5, "page_height_in": 8.75, "bleed_in": .125,
            "panels": {
                "back": [0, 0, 8.5, 8.75], "spine": [8.5, 0, .5, 8.75],
                "front": [9, 0, 8.5, 8.75], "barcode": [7, .4, 1.2, .8],
            },
            "title_box": [10, 6.8, 6, .8], "author_box": [10, .6, 6, .4],
            "blurb_box": [.5, 4, 6, 2],
        }
        font = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
        interior_args = {
            "assets": assets, "pages": pages, "font_path": font,
            "trim_width_in": 8.5, "trim_height_in": 8.5,
            "color_mode": "premium_color", "bleed": False,
            "inside_margin_in": .375, "outside_margin_in": .25,
            "top_margin_in": .25, "bottom_margin_in": .25, "dpi_target": 1,
        }
        cover_args = {
            "template_pdf_path": template, "template_sha256": template_hash,
            "template_layout": layout, "back_art": cover_assets[0],
            "front_art": cover_assets[1], "title": "Nia et la rivière",
            "author": "Auteur confirmé",
            "blurb": "Une histoire illustrée pour apprendre à observer et protéger son environnement.",
            "font_path": font, "page_count": 24, "dpi_target": 100,
        }
        return upload, interior_args, cover_args

    def test_builds_two_separate_pdfs_and_pending_manifest_atomically(self):
        with tempfile.TemporaryDirectory() as root:
            upload, interior, cover = self.setup_sources(root)
            result = build_kdp_print_package(
                storage_root=root, upload_id=upload,
                interior_args=interior, cover_args=cover,
            )
            package = Path(result["package_dir"])
            manifest = json.loads((package / "package-manifest.json").read_text())
            self.assertTrue((package / "interior.pdf").read_bytes().startswith(b"%PDF-"))
            self.assertTrue((package / "cover.pdf").read_bytes().startswith(b"%PDF-"))
            self.assertEqual(manifest["interior"]["page_count"], 24)
            self.assertEqual(manifest["cover"]["page_count"], 1)
            self.assertEqual(manifest["interior"]["preflight"], "pending_manual_visual_inspection")
            self.assertFalse(result["kdp_submission_ready"])
            self.assertFalse(result["publication_performed"])

    def test_rolls_back_partial_package_when_cover_fails(self):
        with tempfile.TemporaryDirectory() as root:
            upload, interior, cover = self.setup_sources(root)
            cover["template_sha256"] = "0" * 64
            with self.assertRaises(Exception):
                build_kdp_print_package(
                    storage_root=root, upload_id=upload,
                    interior_args=interior, cover_args=cover,
                )
            self.assertFalse((Path(root) / upload / "kdp-package-v001").exists())
            self.assertFalse(any(p.name.startswith(".kdp-package-") for p in (Path(root) / upload).iterdir()))

    def test_cannot_override_controlled_paths(self):
        with tempfile.TemporaryDirectory() as root:
            upload, interior, cover = self.setup_sources(root)
            interior["output_path"] = "/tmp/unsafe.pdf"
            with self.assertRaises(KDPPrintPackageError):
                build_kdp_print_package(
                    storage_root=root, upload_id=upload,
                    interior_args=interior, cover_args=cover,
                )


if __name__ == "__main__":
    unittest.main()
