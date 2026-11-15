import hashlib
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
import reportlab
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

from papi_core.papi_kids_kdp_cover import KDPCoverError, build_kdp_full_wrap_cover_pdf


def png_chunk(kind, payload):
    return (len(payload).to_bytes(4, "big") + kind + payload +
            (zlib.crc32(kind + payload) & 0xffffffff).to_bytes(4, "big"))


def png_fixture(width=900, height=900):
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    row = b"\x00" + b"\x22\x88\xaa\xff" * width
    pixels = zlib.compress(row * height)
    return (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", header) +
            png_chunk(b"IDAT", pixels) + png_chunk(b"IEND", b""))


class PapiKidsKDPCoverTests(unittest.TestCase):
    def setup_cover(self, root):
        upload = "PKP-UP-" + "c" * 32
        cover_dir = Path(root) / upload / "covers"
        cover_dir.mkdir(parents=True)
        image_bytes = png_fixture()
        assets = []
        for name in ("back", "front"):
            path = cover_dir / f"{name}.png"
            path.write_bytes(image_bytes)
            assets.append({
                "review_status": "approved",
                "storage_key": f"{upload}/covers/{name}.png",
                "media_type": "image/png",
                "width_px": 900, "height_px": 900,
                "sha256": hashlib.sha256(image_bytes).hexdigest(),
                "target_rect_in": [0, 0, 3, 3],
            })
        template = Path(root) / "official-kdp-template.pdf"
        template_pdf = canvas.Canvas(str(template), pagesize=(17.5 * inch, 8.75 * inch), invariant=1)
        template_pdf.showPage()
        template_pdf.save()
        template_hash = hashlib.sha256(template.read_bytes()).hexdigest()
        layout = {
            "source_template_sha256": template_hash,
            "page_width_in": 17.5, "page_height_in": 8.75, "bleed_in": .125,
            "panels": {
                "back": [0, 0, 8.5, 8.75],
                "spine": [8.5, 0, .5, 8.75],
                "front": [9, 0, 8.5, 8.75],
                "barcode": [7, .4, 1.2, .8],
            },
            "title_box": [10, 6.8, 6, .8],
            "author_box": [10, .6, 6, .4],
            "blurb_box": [.5, 4, 6, 2],
        }
        font = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
        return upload, template, template_hash, layout, assets, font

    def test_builds_one_page_wrap_and_leaves_barcode_blank(self):
        with tempfile.TemporaryDirectory() as root:
            upload, template, digest, layout, assets, font = self.setup_cover(root)
            output = Path(root) / "cover.pdf"
            result = build_kdp_full_wrap_cover_pdf(
                root, output, upload_id=upload, template_pdf_path=template,
                template_sha256=digest, template_layout=layout,
                back_art=assets[0], front_art=assets[1],
                title="Nia et la rivière", author="Auteur confirmé",
                blurb="Une histoire illustrée pour apprendre à observer et protéger son environnement.",
                font_path=font, page_count=24, dpi_target=100,
            )
            self.assertTrue(output.read_bytes().startswith(b"%PDF-"))
            self.assertEqual(result["page_count"], 1)
            self.assertTrue(result["barcode_zone_left_blank"])
            self.assertFalse(result["kdp_submission_ready"])

    def test_rejects_changed_template(self):
        with tempfile.TemporaryDirectory() as root:
            upload, template, digest, layout, assets, font = self.setup_cover(root)
            template.write_bytes(b"%PDF-1.7\nTAMPERED")
            with self.assertRaises(KDPCoverError):
                build_kdp_full_wrap_cover_pdf(
                    root, Path(root) / "cover.pdf", upload_id=upload,
                    template_pdf_path=template, template_sha256=digest,
                    template_layout=layout, back_art=assets[0], front_art=assets[1],
                    title="Nia", author="Auteur", blurb="Résumé de l'histoire.",
                    font_path=font, page_count=24, dpi_target=100,
                )

    def test_rejects_unapproved_cover_art(self):
        with tempfile.TemporaryDirectory() as root:
            upload, template, digest, layout, assets, font = self.setup_cover(root)
            assets[1]["review_status"] = "pending_review"
            with self.assertRaises(KDPCoverError):
                build_kdp_full_wrap_cover_pdf(
                    root, Path(root) / "cover.pdf", upload_id=upload,
                    template_pdf_path=template, template_sha256=digest,
                    template_layout=layout, back_art=assets[0], front_art=assets[1],
                    title="Nia", author="Auteur", blurb="Résumé de l'histoire.",
                    font_path=font, page_count=24, dpi_target=100,
                )

    def test_rejects_spine_text_under_80_pages(self):
        with tempfile.TemporaryDirectory() as root:
            upload, template, digest, layout, assets, font = self.setup_cover(root)
            layout["spine_text_box"] = [8.55, 3, .4, .3]
            with self.assertRaises(KDPCoverError):
                build_kdp_full_wrap_cover_pdf(
                    root, Path(root) / "cover.pdf", upload_id=upload,
                    template_pdf_path=template, template_sha256=digest,
                    template_layout=layout, back_art=assets[0], front_art=assets[1],
                    title="Nia", author="Auteur", blurb="Résumé de l'histoire.",
                    font_path=font, page_count=24, dpi_target=100,
                )


if __name__ == "__main__":
    unittest.main()
