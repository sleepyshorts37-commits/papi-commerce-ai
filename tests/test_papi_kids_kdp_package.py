import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from papi_core.papi_kids_kdp_package import (
    PapiKidsKDPPrintPackageError,
    build_kdp_print_package,
)


class PapiKidsKDPPrintPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.upload = "PKP-UP-" + "a" * 32
        self.book_dir = self.root / self.upload
        self.book_dir.mkdir()
        self.template_path = self.book_dir / "official-cover-template.pdf"
        self.template_path.write_bytes(b"%PDF-1.7 official template")
        self.template = {
            "template_path": str(self.template_path),
            "template_sha256": hashlib.sha256(self.template_path.read_bytes()).hexdigest(),
            "source_url": "https://kdp.amazon.com/cover-calculator",
            "downloaded_at": "2026-11-15T12:00:00Z",
        }
        self.pages = [{"page_number": i, "text": f"Page {i}", "text_box": {"x": .5, "y": .5, "width": 7, "height": 7}} for i in range(1,25)]
        self.assets = [{"page_number": i, "review_status": "approved"} for i in range(1,25)]
        self.cover_asset = {"review_status": "approved", "storage_key": "covers/front.png"}
        self.interior_args = {
            "pages": self.pages, "assets": self.assets, "color_mode": "premium_color",
            "bleed": True, "trim_width_in": 8.5, "trim_height_in": 8.5,
        }
        self.cover_args = {
            "page_count": 24, "trim_width_in": 8.5, "trim_height_in": 8.5,
            "paper_type": "color", "cover_template": self.template,
            "front_asset": self.cover_asset, "back_asset": self.cover_asset,
            "title": "Nia", "author": "Auteur confirmé",
        }

    def tearDown(self):
        self.temp.cleanup()

    def builders(self, fail_cover=False):
        def interior(root, output, **kwargs):
            Path(output).write_bytes(b"%PDF-1.7 interior")
            return {"output_path": str(output), "page_count": 24}
        def cover(root, output, **kwargs):
            if fail_cover:
                raise RuntimeError("cover generation failed")
            Path(output).write_bytes(b"%PDF-1.7 cover")
            return {"output_path": str(output), "page_count": 1}
        return interior, cover

    def test_builds_atomic_package_and_manifest_for_manual_review(self):
        interior, cover = self.builders()
        with patch("papi_core.papi_kids_kdp_package.build_interior_pdf", side_effect=interior), patch(
            "papi_core.papi_kids_kdp_package.build_kdp_cover_pdf", side_effect=cover
        ):
            result = build_kdp_print_package(
                storage_root=self.root, upload_id=self.upload,
                interior_args=self.interior_args, cover_args=self.cover_args,
            )
        manifest = json.loads(Path(result["manifest_path"]).read_text())
        self.assertEqual(manifest["pdfs"]["interior"]["page_count"], 24)
        self.assertEqual(manifest["pdfs"]["cover"]["page_count"], 1)
        self.assertEqual(manifest["pdfs"]["interior"]["preflight"], "pending_manual_pdf_inspection")
        self.assertFalse(result["kdp_upload_ready"])
        self.assertFalse(result["publication_performed"])
        self.assertEqual((Path(result["package_dir"]) / "package-manifest.json").stat().st_mode & 0o777, 0o600)

    def ebook_args(self):
        return {
            "title": "Nia", "author": "Auteur confirmé", "language": "fr",
            "identifier": "urn:papi:PKP-0001",
            "modified_at": "2026-11-15T12:00:00Z",
            "pages": self.pages,
            "page_assets": [{"review_status": "approved"} for _ in range(24)],
            "cover_asset": {"review_status": "approved"},
            "canvas_width_px": 9, "canvas_height_px": 9, "font_path": "/font.ttf",
        }

    def test_builds_print_and_ebook_together_with_shared_manifest(self):
        interior, cover = self.builders()
        def ebook(root, output, upload_id, **kwargs):
            Path(output).write_bytes(b"PK\x03\x04fake-epub")
            return {"output_path": str(output), "page_count": 24}
        with patch("papi_core.papi_kids_kdp_package.build_interior_pdf", side_effect=interior), patch(
            "papi_core.papi_kids_kdp_package.build_kdp_cover_pdf", side_effect=cover
        ), patch(
            "papi_core.papi_kids_kdp_package.build_kdp_fixed_layout_epub", side_effect=ebook
        ), patch(
            "papi_core.papi_kids_kdp_package.validate_epub_structure",
            return_value={"fixed_layout": True, "kindle_previewer_passed": False}
        ):
            result = build_kdp_print_package(
                storage_root=self.root, upload_id=self.upload,
                interior_args=self.interior_args, cover_args=self.cover_args,
                ebook_args=self.ebook_args(), ebook_required=True,
            )
        manifest = json.loads(Path(result["manifest_path"]).read_text())
        self.assertTrue(manifest["ebook_required"])
        self.assertEqual(manifest["ebook"]["page_count"], 24)
        self.assertEqual(manifest["ebook"]["preflight"], "pending_kindle_previewer")
        self.assertTrue((Path(result["package_dir"]) / "book.epub").is_file())
        self.assertFalse(result["kdp_upload_ready"])

    def test_required_ebook_without_assets_blocks_package(self):
        interior, cover = self.builders()
        with patch("papi_core.papi_kids_kdp_package.build_interior_pdf") as build:
            with self.assertRaises(PapiKidsKDPPrintPackageError):
                build_kdp_print_package(
                    storage_root=self.root, upload_id=self.upload,
                    interior_args=self.interior_args, cover_args=self.cover_args,
                    ebook_required=True,
                )
            build.assert_not_called()

    def test_ebook_page_text_must_match_print_interior(self):
        interior, cover = self.builders()
        ebook = self.ebook_args()
        ebook["pages"] = [dict(page) for page in self.pages]
        ebook["pages"][0]["text"] = "Texte différent"
        with patch("papi_core.papi_kids_kdp_package.build_interior_pdf") as build:
            with self.assertRaises(PapiKidsKDPPrintPackageError):
                build_kdp_print_package(
                    storage_root=self.root, upload_id=self.upload,
                    interior_args=self.interior_args, cover_args=self.cover_args,
                    ebook_args=ebook,
                )
            build.assert_not_called()

    def test_unapproved_asset_blocks_before_any_pdf_builder(self):
        interior, cover = self.builders()
        assets = [dict(item) for item in self.assets]
        assets[0]["review_status"] = "pending_review"
        args = dict(self.interior_args, assets=assets)
        with patch("papi_core.papi_kids_kdp_package.build_interior_pdf") as build:
            with self.assertRaises(PapiKidsKDPPrintPackageError):
                build_kdp_print_package(
                    storage_root=self.root, upload_id=self.upload,
                    interior_args=args, cover_args=self.cover_args,
                )
            build.assert_not_called()

    def test_interior_and_cover_trim_sizes_must_match(self):
        interior, cover = self.builders()
        args = dict(self.cover_args, trim_width_in=6.0)
        with patch("papi_core.papi_kids_kdp_package.build_interior_pdf") as build:
            with self.assertRaises(PapiKidsKDPPrintPackageError):
                build_kdp_print_package(
                    storage_root=self.root, upload_id=self.upload,
                    interior_args=self.interior_args, cover_args=args,
                )
            build.assert_not_called()

    def test_invalid_page_identifiers_fail_closed(self):
        assets = [dict(item) for item in self.assets]
        assets[0]["page_number"] = None
        args = dict(self.interior_args, assets=assets)
        with self.assertRaises(PapiKidsKDPPrintPackageError):
            build_kdp_print_package(
                storage_root=self.root, upload_id=self.upload,
                interior_args=args, cover_args=self.cover_args,
            )

    def test_template_hash_mismatch_blocks_package(self):
        interior, cover = self.builders()
        template = dict(self.template, template_sha256="0" * 64)
        args = dict(self.cover_args, cover_template=template)
        with patch("papi_core.papi_kids_kdp_package.build_interior_pdf") as build:
            with self.assertRaises(PapiKidsKDPPrintPackageError):
                build_kdp_print_package(
                    storage_root=self.root, upload_id=self.upload,
                    interior_args=self.interior_args, cover_args=args,
                )
            build.assert_not_called()

    def test_failure_rolls_back_staging_and_does_not_publish_partial_package(self):
        interior, cover = self.builders(fail_cover=True)
        with patch("papi_core.papi_kids_kdp_package.build_interior_pdf", side_effect=interior), patch(
            "papi_core.papi_kids_kdp_package.build_kdp_cover_pdf", side_effect=cover
        ):
            with self.assertRaises(PapiKidsKDPPrintPackageError):
                build_kdp_print_package(
                    storage_root=self.root, upload_id=self.upload,
                    interior_args=self.interior_args, cover_args=self.cover_args,
                )
        self.assertFalse((self.book_dir / "kdp-print-package-v001").exists())
        self.assertEqual(list(self.book_dir.glob(".kdp-print-package-*")), [])


if __name__ == "__main__":
    unittest.main()
