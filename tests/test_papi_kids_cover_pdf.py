import hashlib
import tempfile
import unittest
from pathlib import Path

from PIL import Image
import reportlab

from papi_core.papi_kids_cover_pdf import KDPCoverError, build_kdp_cover_pdf


def make_asset(root, key, filename):
    path = Path(root) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (9, 9), (120, 150, 180)).save(path, format="PNG")
    data = path.read_bytes()
    return {
        "storage_key": key, "sha256": hashlib.sha256(data).hexdigest(),
        "media_type": "image/png", "width_px": 9, "height_px": 9,
        "review_status": "approved",
    }


def template(root):
    path = Path(root) / "kdp-template.pdf"
    path.write_bytes(b"%PDF-1.7\nKDP official template fixture\n")
    return {
        "template_path": str(path),
        "template_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_url": "https://kdp.amazon.com/help/topic/G201857950",
        "downloaded_at": "2026-11-15",
        "page_width_in": 17.306328, "page_height_in": 8.75,
        "back_panel": {"x": 0, "y": 0, "width": 8.625, "height": 8.75},
        "spine_box": {"x": 8.625, "y": 0, "width": .056328, "height": 8.75},
        "front_panel": {"x": 8.681328, "y": 0, "width": 8.625, "height": 8.75},
        "barcode_box": {"x": .5, "y": .5, "width": 2, "height": 1.2},
        "summary_box": {"x": .5, "y": 3, "width": 7, "height": 2.5},
        "title_box": {"x": 9.1, "y": 6.5, "width": 7, "height": 1.2},
        "author_box": {"x": 9.1, "y": 1, "width": 7, "height": .5},
    }


class PapiKidsCoverPDFTests(unittest.TestCase):
    def test_builds_cover_pdf_from_approved_art_and_official_template(self):
        with tempfile.TemporaryDirectory() as root:
            front = make_asset(root, "covers/front.png", "front.png")
            back = make_asset(root, "covers/back.png", "back.png")
            config = template(root)
            font = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
            output = Path(root) / "cover.pdf"
            result = build_kdp_cover_pdf(
                root, output, trim_width_in=8.5, trim_height_in=8.5,
                page_count=24, paper_type="color", cover_template=config,
                front_asset=front, back_asset=back,
                title="Nia et la rivière aux mille reflets", author="Auteur confirmé",
                back_cover_text="Nia découvre que la rivière a changé. Avec ses amis, elle apprend à observer et agir avec les adultes.",
                font_path=font, dpi_target=1,
            )
            self.assertTrue(output.read_bytes().startswith(b"%PDF-"))
            self.assertEqual(result["page_count"], 1)
            self.assertTrue(result["barcode_reserved"])
            self.assertFalse(result["kdp_submission_ready"])

    def test_rejects_unapproved_cover_art(self):
        with tempfile.TemporaryDirectory() as root:
            front = make_asset(root, "covers/front.png", "front.png")
            back = make_asset(root, "covers/back.png", "back.png")
            front["review_status"] = "pending_review"
            with self.assertRaises(KDPCoverError):
                build_kdp_cover_pdf(
                    root, Path(root) / "cover.pdf", trim_width_in=8.5, trim_height_in=8.5,
                    page_count=24, paper_type="color", cover_template=template(root),
                    front_asset=front, back_asset=back,
                    title="Nia", author="Auteur",
                    back_cover_text="Nia découvre que la rivière a changé et apprend à agir avec ses amis.",
                    font_path=Path(reportlab.__file__).parent / "fonts" / "Vera.ttf", dpi_target=1,
                )

    def test_rejects_template_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as root:
            front = make_asset(root, "covers/front.png", "front.png")
            back = make_asset(root, "covers/back.png", "back.png")
            config = template(root)
            config["template_sha256"] = "0" * 64
            with self.assertRaises(KDPCoverError):
                build_kdp_cover_pdf(
                    root, Path(root) / "cover.pdf", trim_width_in=8.5, trim_height_in=8.5,
                    page_count=24, paper_type="color", cover_template=config,
                    front_asset=front, back_asset=back,
                    title="Nia", author="Auteur",
                    back_cover_text="Nia découvre que la rivière a changé et apprend à agir avec ses amis.",
                    font_path=Path(reportlab.__file__).parent / "fonts" / "Vera.ttf", dpi_target=1,
                )


if __name__ == "__main__":
    unittest.main()
