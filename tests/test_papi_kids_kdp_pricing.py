import unittest

from papi_core.papi_kids_kdp_pricing import KDPPriceError, calculate_paperback_price


class PapiKidsKDPPriceTests(unittest.TestCase):
    def test_24_page_8_5_square_premium_color_us_cost_and_royalty(self):
        result = calculate_paperback_price(
            marketplace="amazon.com", page_count=24,
            trim_width_in=8.5, trim_height_in=8.5,
            color_mode="premium_color", list_price="12.99",
        )
        self.assertEqual(result["trim_class"], "large")
        self.assertEqual(result["printing_cost"], "4.20")
        self.assertEqual(result["royalty_rate"], "0.60")
        self.assertEqual(result["estimated_royalty"], "3.59")
        self.assertTrue(result["estimate_only"])
        self.assertFalse(result["currency_conversion_performed"])

    def test_standard_color_is_not_available_at_24_pages(self):
        with self.assertRaises(KDPPriceError):
            calculate_paperback_price(
                marketplace="amazon.com", page_count=24,
                trim_width_in=8.5, trim_height_in=8.5,
                color_mode="standard_color", list_price="12.99",
            )

    def test_42_page_premium_cost_uses_per_page_rate(self):
        result = calculate_paperback_price(
            marketplace="amazon.com", page_count=42,
            trim_width_in=8.5, trim_height_in=8.5,
            color_mode="premium_color", list_price="12.99",
        )
        self.assertEqual(result["printing_cost"], "4.36")
        self.assertEqual(result["printing_cost_formula"],
                         "fixed_cost_plus_page_count_times_premium_per_page")

    def test_low_price_below_minimum_is_rejected(self):
        with self.assertRaises(KDPPriceError):
            calculate_paperback_price(
                marketplace="amazon.com", page_count=24,
                trim_width_in=8.5, trim_height_in=8.5,
                color_mode="premium_color", list_price="7.99",
            )

    def test_price_threshold_selects_50_percent_tier(self):
        result = calculate_paperback_price(
            marketplace="amazon.com", page_count=24,
            trim_width_in=8.5, trim_height_in=8.5,
            color_mode="premium_color", list_price="9.98",
        )
        self.assertEqual(result["royalty_rate"], "0.50")
        self.assertEqual(result["estimated_royalty"], "0.79")

    def test_expanded_distribution_uses_40_percent(self):
        result = calculate_paperback_price(
            marketplace="amazon.com", page_count=24,
            trim_width_in=8.5, trim_height_in=8.5,
            color_mode="premium_color", list_price="12.99",
            expanded_distribution=True,
        )
        self.assertEqual(result["royalty_rate"], "0.40")
        self.assertEqual(result["estimated_royalty"], "1.00")

    def test_unknown_marketplace_is_rejected(self):
        with self.assertRaises(KDPPriceError):
            calculate_paperback_price(
                marketplace="amazon.sn", page_count=24,
                trim_width_in=8.5, trim_height_in=8.5,
                color_mode="premium_color", list_price="12.99",
            )


if __name__ == "__main__":
    unittest.main()
