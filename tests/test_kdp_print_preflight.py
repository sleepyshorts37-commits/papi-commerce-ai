import unittest
from datetime import datetime, timedelta, timezone

from papi_core.kdp_print_preflight import (
    KDPPreflightError, validate_kdp_preflight_manifest,
)


def make_template(now=None):
    current = now or datetime.now(timezone.utc)
    return {
        "source_url": "https://kdp.amazon.com/en_US/help/topic/G201834180",
        "template_ref": "official-template-v1",
        "retrieved_at": current.isoformat(),
        "trim_width_in": 8.5, "trim_height_in": 8.5,
        "page_count": 32, "bleed": "bleed", "minimum_dpi": 300,
        "minimum_inner_margin_in": 0.375,
        "minimum_outer_margin_in": 0.25,
        "minimum_top_margin_in": 0.25,
        "minimum_bottom_margin_in": 0.25,
        "minimum_gutter_in": 0.125,
    }


def make_manifest():
    return {
        "interior_pdf": "interior.pdf", "cover_pdf": "cover.pdf",
        "interior_page_count": 32,
        "interior_page_width_in": 8.5, "interior_page_height_in": 8.5,
        "cover_width_in": 17.3, "cover_height_in": 8.75,
        "fonts_embedded": True, "page_order_valid": True,
        "blank_pages_reviewed": True, "pdf_preflight_completed": True,
        "minimum_inner_margin_in": 0.4, "minimum_outer_margin_in": 0.3,
        "minimum_top_margin_in": 0.3, "minimum_bottom_margin_in": 0.3,
        "minimum_gutter_in": 0.15,
        "images": [{"pixel_width": 2550, "pixel_height": 2550,
                    "effective_dpi": 300, "sha256": "a" * 64}
                   for _ in range(24)],
    }


class KDPPrintPreflightTests(unittest.TestCase):
    def test_accepts_complete_measurement_manifest_for_human_review_only(self):
        result = validate_kdp_preflight_manifest(
            template=make_template(), manifest=make_manifest())
        self.assertEqual(result["status"], "ready_for_human_review")
        self.assertFalse(result["kdp_upload_authorized"])

    def test_blocks_bad_resolution_and_missing_images(self):
        manifest = make_manifest()
        manifest["images"][0]["effective_dpi"] = 150
        manifest["images"].pop()
        result = validate_kdp_preflight_manifest(
            template=make_template(), manifest=manifest)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("expected_24_page_images", result["blockers"])
        self.assertIn("image_1_resolution_below_minimum", result["blockers"])

    def test_blocks_wrong_dimensions_and_non_embedded_fonts(self):
        manifest = make_manifest()
        manifest["interior_page_width_in"] = 6
        manifest["fonts_embedded"] = False
        result = validate_kdp_preflight_manifest(
            template=make_template(), manifest=manifest)
        self.assertIn("interior_page_width_in_mismatch", result["blockers"])
        self.assertIn("fonts_not_embedded", result["blockers"])

    def test_rejects_stale_or_non_official_template(self):
        now = datetime.now(timezone.utc)
        with self.assertRaises(KDPPreflightError):
            validate_kdp_preflight_manifest(
                template=make_template(now - timedelta(days=45)),
                manifest=make_manifest(), now=now)
        bad = make_template()
        bad["source_url"] = "https://example.com/kdp-template"
        with self.assertRaises(KDPPreflightError):
            validate_kdp_preflight_manifest(template=bad, manifest=make_manifest())

    def test_rejects_missing_template_dimensions_instead_of_guessing(self):
        template = make_template()
        del template["trim_width_in"]
        with self.assertRaises(KDPPreflightError):
            validate_kdp_preflight_manifest(template=template, manifest=make_manifest())


if __name__ == "__main__":
    unittest.main()
