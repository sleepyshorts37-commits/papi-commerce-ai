import unittest
from runtime.papi_core.opportunity_scanner import normalize_search_results, evaluate_opportunities


def candidate():
    return {
        "title": "Prestation numérique B2B", "url": "https://example.org/offer",
        "verification": {
            "senegal_access": "confirmed", "payment_and_withdrawal": "confirmed",
            "fees": "confirmed", "terms": "confirmed", "legal_compliance": "confirmed",
            "reviewer": "human-reviewer", "reviewed_at": "2026-11-12",
            "evidence_urls": ["https://example.org/terms", "https://example.org/payments"]
        },
        "scoring": {
            "criteria": {"senegal_access": 5, "zero_cost_start": 5, "time_to_first_revenue": 4,
                         "net_margin": 4, "demand_evidence": 4, "low_risk": 5, "operational_fit": 4},
            "estimated_startup_cost_xof": 0, "estimated_days_to_first_revenue": 14,
            "estimated_net_margin_percent": 60
        }
    }


class OpportunityScannerTests(unittest.TestCase):
    def test_normalizes_without_network(self):
        result = normalize_search_results([{"title": "Offer", "url": "https://example.org"}],
                                          collected_at="2026-11-12")
        self.assertEqual(result["items_normalized"], 1)
        self.assertFalse(result["network_accessed"])
        self.assertEqual(result["items"][0]["verification_status"], "needs_verification")

    def test_deduplicates_urls(self):
        result = normalize_search_results([
            {"title": "A", "url": "https://example.org/offer"},
            {"title": "B", "url": "https://example.org/offer/"}
        ], collected_at="2026-11-12")
        self.assertEqual(result["items_normalized"], 1)
        self.assertEqual(result["duplicates_skipped"], 1)

    def test_rejects_http(self):
        result = normalize_search_results([{"title": "Unsafe", "url": "http://example.org"}],
                                          collected_at="2026-11-12")
        self.assertEqual(result["items_rejected"], 1)

    def test_unverified_never_reaches_ranking(self):
        scan = normalize_search_results([{"title": "Unknown", "url": "https://example.org"}],
                                        collected_at="2026-11-12")
        result = evaluate_opportunities(scan)
        self.assertEqual(result["verified_count"], 0)
        self.assertEqual(result["uncertain_count"], 1)
        self.assertEqual(result["top_three"], [])

    def test_attested_candidate_is_scored(self):
        scan = normalize_search_results([candidate()], collected_at="2026-11-12")
        result = evaluate_opportunities(scan)
        self.assertEqual(result["verified_count"], 1)
        self.assertEqual(result["top_three"][0]["decision"], "test")
        self.assertFalse(result["execution_authorized"])

    def test_unconfirmed_payment_blocks_verification(self):
        item = candidate()
        item["verification"]["payment_and_withdrawal"] = "uncertain"
        result = evaluate_opportunities(normalize_search_results([item], collected_at="2026-11-12"))
        self.assertEqual(result["verified_count"], 0)
        self.assertEqual(result["uncertain_count"], 1)


if __name__ == "__main__":
    unittest.main()
