import unittest

from runtime.papi_core.opportunity_pipeline import run_opportunity_pipeline


def candidate(opportunity_id="OPP-001", url="https://example.org/offer"):
    return {
        "opportunity_id": opportunity_id,
        "title": "Prestation numérique B2B",
        "url": url,
        "verification": {
            "senegal_access": "confirmed",
            "payment_and_withdrawal": "confirmed",
            "fees": "confirmed",
            "terms": "confirmed",
            "legal_compliance": "confirmed",
            "reviewer": "human-reviewer",
            "reviewed_at": "2026-11-12",
            "evidence_urls": ["https://example.org/terms", "https://example.org/payments"]
        },
        "scoring": {
            "criteria": {
                "senegal_access": 5, "zero_cost_start": 5, "time_to_first_revenue": 4,
                "net_margin": 4, "demand_evidence": 4, "low_risk": 5, "operational_fit": 4
            },
            "estimated_startup_cost_xof": 0,
            "estimated_days_to_first_revenue": 14,
            "estimated_net_margin_percent": 60
        }
    }


class OpportunityPipelineTests(unittest.TestCase):
    def test_pipeline_creates_manual_review_queue(self):
        result = run_opportunity_pipeline([candidate()], collected_at="2026-11-12")
        self.assertEqual(result["status"], "completed_read_only")
        self.assertEqual(result["summary"]["verified_attestations"], 1)
        self.assertEqual(len(result["manual_review_queue"]), 1)
        self.assertEqual(result["manual_review_queue"][0]["next_step"], "human_review_only")
        self.assertFalse(result["controls"]["execution_authorized"])

    def test_unverified_opportunity_is_not_queued(self):
        raw = {"title": "Unknown", "url": "https://example.org/unknown"}
        result = run_opportunity_pipeline([raw], collected_at="2026-11-12")
        self.assertEqual(result["summary"]["awaiting_verification"], 1)
        self.assertEqual(result["manual_review_queue"], [])

    def test_duplicate_ids_are_rejected(self):
        result = run_opportunity_pipeline([
            candidate("SAME", "https://example.org/one"),
            candidate("SAME", "https://example.org/two")
        ], collected_at="2026-11-12")
        self.assertEqual(result["summary"]["duplicate_ids_rejected"], 1)
        self.assertEqual(result["summary"]["verified_attestations"], 1)

    def test_duplicate_urls_are_skipped(self):
        result = run_opportunity_pipeline([
            candidate("ONE", "https://example.org/offer"),
            candidate("TWO", "https://example.org/offer/")
        ], collected_at="2026-11-12")
        self.assertEqual(result["summary"]["duplicates_skipped"], 1)
        self.assertEqual(result["summary"]["normalized"], 1)

    def test_rejects_non_list_input(self):
        with self.assertRaises(ValueError):
            run_opportunity_pipeline({}, collected_at="2026-11-12")

    def test_rejects_oversized_batch(self):
        with self.assertRaises(ValueError):
            run_opportunity_pipeline([{}] * 201, collected_at="2026-11-12")

    def test_no_external_or_financial_actions(self):
        result = run_opportunity_pipeline([], collected_at="2026-11-12")
        self.assertFalse(result["controls"]["network_accessed"])
        self.assertFalse(result["controls"]["external_actions_enabled"])
        self.assertFalse(result["controls"]["financial_actions_enabled"])
        self.assertEqual(result["controls"]["budget_xof"], 0)


if __name__ == "__main__":
    unittest.main()
