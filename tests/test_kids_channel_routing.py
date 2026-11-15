import copy
import json
import tempfile
import unittest
from pathlib import Path

from papi_core.kids_channel_routing import (
    PLATFORMS, KidsChannelRoutingError, assess_channel,
    build_routing_report, validate_profiles,
)


def profile(platform_id="amazon_kdp"):
    return {
        "platform_id": platform_id,
        "name": platform_id,
        "formats": ["paperback"],
        "senegal_seller_eligibility": "verified",
        "senegal_payout": "verified",
        "territory_coverage": "verified",
        "upfront_cost_xof": 0,
        "subscription_required": "blocked",
        "seller_funds_each_order": "blocked",
        "stock_required": "blocked",
        "direct_print_fulfilment": "verified",
        "evidence": [{"reference": "test-only"}],
        "last_verified": "2026-11-15",
    }


def register(profiles=None):
    profiles = profiles or [profile(pid) for pid in PLATFORMS]
    return {"schema_version": 1, "division_id": "papi_kids_publishing", "profiles": profiles}


class KidsChannelRoutingTests(unittest.TestCase):
    def test_unknown_facts_never_become_eligible(self):
        item = profile()
        for field in ("senegal_seller_eligibility", "senegal_payout", "territory_coverage",
                      "subscription_required", "seller_funds_each_order", "stock_required",
                      "direct_print_fulfilment"):
            item[field] = "unknown"
        item["upfront_cost_xof"] = None
        item["formats"] = []
        result = assess_channel(item, "paperback")
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("zero_upfront_cost", result["facts_to_verify"])
        self.assertFalse(result["publication_authorized"])

    def test_zero_cost_fully_verified_channel_is_eligible(self):
        result = assess_channel(profile(), "paperback")
        self.assertEqual(result["status"], "ELIGIBLE_ZERO_UPFRONT")

    def test_positive_upfront_cost_blocks_channel(self):
        item = profile()
        item["upfront_cost_xof"] = 1
        result = assess_channel(item, "paperback")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("zero_upfront_cost", result["blocked_reasons"])

    def test_stock_and_per_order_advance_block_zero_cash_route(self):
        item = profile("jumia_senegal")
        item["stock_required"] = "verified"
        item["seller_funds_each_order"] = "verified"
        result = assess_channel(item, "paperback")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("no_stock", result["blocked_reasons"])
        self.assertIn("no_per_order_advance", result["blocked_reasons"])

    def test_unknown_format_compatibility_is_hold(self):
        item = profile()
        item["formats"] = []
        result = assess_channel(item, "ebook")
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("format", result["facts_to_verify"])

    def test_known_unsupported_format_is_blocked(self):
        item = profile()
        result = assess_channel(item, "ebook")
        self.assertEqual(result["status"], "BLOCKED")

    def test_unknown_upfront_cost_is_not_treated_as_zero(self):
        item = profile()
        item["upfront_cost_xof"] = None
        result = assess_channel(item, "paperback")
        self.assertEqual(result["status"], "HOLD")

    def test_duplicate_platform_is_rejected(self):
        data = register()
        data["profiles"][1]["platform_id"] = data["profiles"][0]["platform_id"]
        self.assertTrue(any("dupliquée" in error for error in validate_profiles(data)))

    def test_registry_must_cover_exact_platform_set(self):
        data = register()
        data["profiles"].pop()
        self.assertTrue(any("exactement" in error for error in validate_profiles(data)))

    def test_report_has_no_recommendation_when_all_profiles_unknown(self):
        profiles = []
        for pid in PLATFORMS:
            item = profile(pid)
            item.update({
                "formats": [], "senegal_seller_eligibility": "unknown",
                "senegal_payout": "unknown", "territory_coverage": "unknown",
                "upfront_cost_xof": None, "subscription_required": "unknown",
                "seller_funds_each_order": "unknown", "stock_required": "unknown",
                "direct_print_fulfilment": "unknown",
            })
            profiles.append(item)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profiles.json"
            path.write_text(json.dumps(register(profiles)), encoding="utf-8")
            report = build_routing_report("paperback", path=path)
        self.assertEqual(report["recommended_channel"], None)
        self.assertEqual(report["decision"], "NO_VERIFIED_ZERO_COST_CHANNEL")
        self.assertEqual(len(report["hold_channels"]), 6)
        self.assertFalse(report["publication_authorized"])

    def test_invalid_book_format_is_rejected(self):
        with self.assertRaises(KidsChannelRoutingError):
            assess_channel(profile(), "audio")


if __name__ == "__main__":
    unittest.main()
