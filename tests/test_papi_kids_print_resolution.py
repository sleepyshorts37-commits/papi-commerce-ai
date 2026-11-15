import unittest

from papi_core.papi_kids_print_resolution import (
    PrintResolutionError,
    audit_image_resolution,
    audit_illustration_campaign,
)


class PapiKidsPrintResolutionTests(unittest.TestCase):
    def test_1024_square_image_is_not_300_dpi_for_8_5_square_print(self):
        result = audit_image_resolution(
            source_width_px=1024, source_height_px=1024,
            final_width_px=1024, final_height_px=1024,
            trim_width_in=8.5, trim_height_in=8.5, bleed=False,
            output_sha256="a" * 64,
        )
        self.assertEqual(result["source_dpi"], 120.47)
        self.assertEqual(result["required_width_px"], 2550)
        self.assertFalse(result["print_ready"])

    def test_lanczos_upscale_does_not_claim_restored_detail(self):
        result = audit_image_resolution(
            source_width_px=1024, source_height_px=1024,
            final_width_px=2550, final_height_px=2550,
            trim_width_in=8.5, trim_height_in=8.5, bleed=False,
            output_sha256="b" * 64, upscaling_method="lanczos_only",
        )
        self.assertTrue(result["final_pixel_pass"])
        self.assertFalse(result["source_detail_pass"])
        self.assertFalse(result["print_ready"])

    def test_ai_super_resolution_requires_human_review_bound_to_output_hash(self):
        review = {"approved": True, "reviewer_id": "editor-01",
                  "approved_at": "2026-11-15", "output_sha256": "c" * 64}
        result = audit_image_resolution(
            source_width_px=1024, source_height_px=1024,
            final_width_px=2550, final_height_px=2550,
            trim_width_in=8.5, trim_height_in=8.5, bleed=False,
            output_sha256="c" * 64, upscaling_method="ai_super_resolution",
            resolution_review=review,
        )
        self.assertTrue(result["print_ready"])
        review["output_sha256"] = "d" * 64
        result = audit_image_resolution(
            source_width_px=1024, source_height_px=1024,
            final_width_px=2550, final_height_px=2550,
            trim_width_in=8.5, trim_height_in=8.5, bleed=False,
            output_sha256="c" * 64, upscaling_method="ai_super_resolution",
            resolution_review=review,
        )
        self.assertFalse(result["print_ready"])

    def test_bleed_increases_required_pixel_dimensions(self):
        result = audit_image_resolution(
            source_width_px=2588, source_height_px=2625,
            final_width_px=2588, final_height_px=2625,
            trim_width_in=8.5, trim_height_in=8.5, bleed=True,
            output_sha256="e" * 64,
        )
        self.assertEqual(result["required_width_px"], 2588)
        self.assertEqual(result["required_height_px"], 2625)
        self.assertTrue(result["print_ready"])

    def test_campaign_reports_all_blocked_pages(self):
        assets = [{
            "page_number": i, "source_width_px": 1024, "source_height_px": 1024,
            "width_px": 1024, "height_px": 1024, "sha256": f"{i:064x}",
        } for i in range(1, 25)]
        result = audit_illustration_campaign(
            assets, page_count=24, trim_width_in=8.5, trim_height_in=8.5, bleed=False,
        )
        self.assertFalse(result["print_ready"])
        self.assertEqual(len(result["blocked_pages"]), 24)

    def test_rejects_invalid_hash(self):
        with self.assertRaises(PrintResolutionError):
            audit_image_resolution(
                source_width_px=100, source_height_px=100,
                final_width_px=100, final_height_px=100,
                trim_width_in=5, trim_height_in=5, bleed=False,
                output_sha256="not-a-hash",
            )


if __name__ == "__main__":
    unittest.main()
