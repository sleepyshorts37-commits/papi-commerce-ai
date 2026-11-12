import unittest

from runtime.papi_core.opportunity_scoring import rank_opportunities, score_opportunity


def sample(**overrides):
    record = {
        "opportunity_id": "OPP-001",
        "title": "Service numérique B2B",
        "source": "https://example.org/public-offer",
        "source_checked_at": "2026-11-12",
        "country_access": "confirmed",
        "legal_status": "compliant",
        "payment_access": "confirmed",
        "evidence_level": "verified",
        "criteria": {
            "senegal_access": 5, "zero_cost_start": 5, "time_to_first_revenue": 4,
            "net_margin": 4, "demand_evidence": 4, "low_risk": 5, "operational_fit": 4,
        },
        "estimated_startup_cost_xof": 0,
        "estimated_days_to_first_revenue": 14,
        "estimated_net_margin_percent": 70,
        "notes": "",
    }
    record.update(overrides)
    return record


class OpportunityScoringTests(unittest.TestCase):
    def test_high_score_can_be_test_candidate(self):
        result = score_opportunity(sample())
        self.assertEqual(result["decision"], "test")
        # Weighted score: (5*20 + 5*15 + 4*15 + 4*15 + 4*15 + 5*10 + 4*10) / 5 = 89.
        self.assertEqual(result["score"], 89)
        self.assertFalse(result["execution_authorized"])

    def test_unconfirmed_senegal_access_blocks_test(self):
        result = score_opportunity(sample(country_access="uncertain"))
        self.assertNotEqual(result["decision"], "test")
        self.assertTrue(result["gate_status"]["blockers"])

    def test_prohibited_activity_is_rejected(self):
        result = score_opportunity(sample(legal_status="prohibited"))
        self.assertEqual(result["decision"], "reject")

    def test_unknown_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            score_opportunity(sample(personal_phone="123"))

    def test_rank_returns_maximum_three_candidates(self):
        records = [sample(opportunity_id=f"OPP-{i}") for i in range(5)]
        result = rank_opportunities(records)
        self.assertEqual(len(result["top_three"]), 3)
        self.assertEqual(result["opportunities_scored"], 5)

    def test_invalid_criterion_is_rejected_by_ranker(self):
        record = sample()
        record["criteria"]["low_risk"] = 9
        result = rank_opportunities([record])
        self.assertEqual(result["inputs_rejected"], 1)
        self.assertEqual(result["opportunities_scored"], 0)


if __name__ == "__main__":
    unittest.main()
