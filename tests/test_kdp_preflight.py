"""Tests des formules officielles de gabarit paperback KDP."""
import unittest

from papi_core.kdp_preflight import (
    KdpPreflightError, calculate_paperback_cover, paperback_minimum_margins,
)


class KdpPreflightTests(unittest.TestCase):
    def test_white_paper_cover_width_and_height(self):
        spec = calculate_paperback_cover(8.5, 8.5, 100, "white")
        self.assertEqual(spec.spine_width_in, round(100 * 0.002252, 5))
        self.assertEqual(spec.full_cover_width_in, round(17.0 + 100 * 0.002252 + 0.25, 5))
        self.assertEqual(spec.full_cover_height_in, 8.75)
        self.assertTrue(spec.spine_text_allowed)

    def test_spine_text_is_disabled_below_80_pages(self):
        self.assertFalse(calculate_paperback_cover(8.5, 8.5, 79, "white").spine_text_allowed)
        self.assertTrue(calculate_paperback_cover(8.5, 8.5, 80, "white").spine_text_allowed)

    def test_all_paper_coefficients_are_supported(self):
        for paper in ("white", "cream", "groundwood", "premium_color", "standard_color"):
            self.assertGreater(calculate_paperback_cover(6, 9, 120, paper).spine_width_in, 0)

    def test_gutter_increases_with_page_count(self):
        self.assertEqual(paperback_minimum_margins(100)["inside_gutter_in"], 0.375)
        self.assertEqual(paperback_minimum_margins(200)["inside_gutter_in"], 0.5)
        self.assertEqual(paperback_minimum_margins(400)["inside_gutter_in"], 0.625)
        self.assertEqual(paperback_minimum_margins(600)["inside_gutter_in"], 0.75)
        self.assertEqual(paperback_minimum_margins(750)["inside_gutter_in"], 0.875)

    def test_bleed_changes_outer_margins(self):
        self.assertEqual(paperback_minimum_margins(100, bleed=False)["outside_min_in"], 0.25)
        self.assertEqual(paperback_minimum_margins(100, bleed=True)["outside_min_in"], 0.375)

    def test_invalid_page_count_and_paper_are_rejected(self):
        with self.assertRaises(KdpPreflightError):
            calculate_paperback_cover(6, 9, 10, "white")
        with self.assertRaises(KdpPreflightError):
            calculate_paperback_cover(6, 9, 100, "unknown")


if __name__ == "__main__":
    unittest.main()
