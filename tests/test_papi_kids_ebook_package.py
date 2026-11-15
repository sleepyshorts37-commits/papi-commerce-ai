import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
import reportlab

from papi_core.papi_kids_ebook_package import (
    PapiKidsEPUBPackageError,
    build_kdp_ebook_package,
    validate_epub_structure,
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


class PapiKidsEbookPackageTests(unittest.TestCase):
    def setup_package(self, root):
        upload = "PKP-UP-" + "f" * 32
        (Path(root) / upload).mkdir()
        cover = asset(root, "covers/ebook-cover.png")
        images = [
            asset(root, f"{upload}/illustrations/page-{n:02d}.png", n)
            for n in range(1, 25)
        ]
        pages = [{
            "page_number": n, "text": f"Nia observe la rivière, page {n}.",
            "text_box": {"x": 8, "y": 8, "width": 75, "height": 20},
        } for n in range(1, 25)]
        font = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
        args = {
            "title": "Nia et la rivière aux mille reflets",
            "author": "Auteur confirmé", "language": "fr",
            "identifier": "urn:papi:PKP-0001",
            "modified_at": "2026-11-15T22:00:00Z",
            "pages": pages, "page_assets": images, "cover_asset": cover,
            "canvas_width_px": 9, "canvas_height_px": 9, "font_path": font,
        }
        return upload, args

    def test_builds_private_epub_package_and_manifest(self):
        with tempfile.TemporaryDirectory() as root:
            upload, args = self.setup_package(root)
            result = build_kdp_ebook_package(
                storage_root=root, upload_id=upload, epub_args=args,
            )
            package = Path(result["package_dir"])
            manifest = json.loads((package / "ebook-manifest.json").read_text())
            self.assertTrue((package / "book.epub").is_file())
            self.assertEqual(manifest["ebook"]["page_count"], 24)
            self.assertEqual(manifest["ebook"]["preflight"], "pending_kindle_previewer")
            self.assertFalse(result["kdp_upload_ready"])
            self.assertEqual((package / "ebook-manifest.json").stat().st_mode & 0o777, 0o600)

    def test_rolls_back_when_ebook_assets_fail(self):
        with tempfile.TemporaryDirectory() as root:
            upload, args = self.setup_package(root)
            args["page_assets"][0]["review_status"] = "pending_review"
            with self.assertRaises(Exception):
                build_kdp_ebook_package(storage_root=root, upload_id=upload, epub_args=args)
            self.assertFalse((Path(root) / upload / "ebook-package-v001").exists())

    def test_rejects_epub_with_wrong_page_count(self):
        with tempfile.TemporaryDirectory() as root:
            upload, args = self.setup_package(root)
            result = build_kdp_ebook_package(storage_root=root, upload_id=upload, epub_args=args)
            with self.assertRaises(PapiKidsEPUBPackageError):
                validate_epub_structure(Path(result["package_dir"]) / "book.epub", 23)


if __name__ == "__main__":
    unittest.main()
