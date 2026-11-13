import unittest

from papi_core.global_work_ranking import rank_global_work_opportunities


def candidate(candidate_id="lead-1", **overrides):
    item = {
        "candidate_id": candidate_id, "source_id": "source-a", "title": "Remote task",
        "source_url": "https://example.org/task/" + candidate_id,
        "published_at": "2026-11-12T10:00:00Z",
        "eligibility": {
            "eligible_countries": ["SN"],
            "payout": {"amount": "100", "currency": "USD", "methods": ["PayPal"]},
            "fees": "5", "upfront_cost": "0", "estimated_hours": "4",
            "kyc_required": True, "ai_policy": "allowed", "human_presence": "not_required",
            "evidence": {k: "https://example.org/" + k for k in
                ("country_eligibility", "payout_terms", "fees", "kyc", "ai_policy")},
        },
    }
    item.update(overrides)
    return item


def registry(status="verified", enabled=True):
    source = {
        "source_id": "source-a", "name": "Example", "source_type": "job_board",
        "url": "https://example.org", "access_mode": "manual",
        "verification_status": status, "eligible_countries": ["SN"],
        "payout_methods": ["PayPal"], "enabled": enabled,
    }
    if status == "verified":
        source.update({
            "verification_evidence": {
                "country_eligibility_url": "https://example.org/countries",
                "payout_terms_url": "https://example.org/payout",
                "terms_url": "https://example.org/terms",
            },
            "verified_at": "2026-11-12T10:00:00Z", "verified_by": "human",
        })
    return {"sources": [source]}


class GlobalWorkRankingTests(unittest.TestCase):
    def test_complete_fresh_supported_lead_is_prioritized_not_approved(self):
        result = rank_global_work_opportunities(
            [candidate()], now="2026-11-13T10:00:00Z",
            source_registry=registry(),
            evidence_reviews={"source-a": {"overall_status": "human_review_required"}},
        )
        lead = result["results"][0]
        self.assertEqual(lead["ranking_status"], "priority_for_human_review")
        self.assertGreaterEqual(lead["priority_score"], 50)
        self.assertFalse(lead["qualified"])
        self.assertFalse(lead["application_submitted"])
        self.assertFalse(result["external_actions_performed"])

    def test_country_not_listed_blocks_priority(self):
        item = candidate()
        item["eligibility"]["eligible_countries"] = ["US"]
        result = rank_global_work_opportunities(
            [item], now="2026-11-13T10:00:00Z", source_registry=registry(),
            evidence_reviews={"source-a": {"overall_status": "human_review_required"}},
        )
        self.assertIn("pays_demandeur_non_admissible", result["results"][0]["ranking_blockers"])
        self.assertEqual(result["results"][0]["ranking_status"], "hold_for_review")

    def test_contradictory_evidence_blocks_priority(self):
        result = rank_global_work_opportunities(
            [candidate()], now="2026-11-13T10:00:00Z", source_registry=registry(),
            evidence_reviews={"source-a": {"overall_status": "contradiction_detected"}},
        )
        self.assertIn("preuves_contradictoires", result["results"][0]["ranking_blockers"])

    def test_unverified_source_cannot_become_priority(self):
        result = rank_global_work_opportunities(
            [candidate()], now="2026-11-13T10:00:00Z", source_registry=registry("unverified"),
            evidence_reviews={"source-a": {"overall_status": "human_review_required"}},
        )
        self.assertEqual(result["results"][0]["ranking_status"], "hold_for_review")

    def test_negative_net_blocks_priority(self):
        item = candidate()
        item["eligibility"]["fees"] = "150"
        result = rank_global_work_opportunities(
            [item], now="2026-11-13T10:00:00Z", source_registry=registry(),
            evidence_reviews={"source-a": {"overall_status": "human_review_required"}},
        )
        self.assertIn("revenu_net_non_positif", result["results"][0]["ranking_blockers"])

    def test_unknown_publication_date_is_not_treated_as_fresh(self):
        item = candidate()
        item.pop("published_at")
        result = rank_global_work_opportunities([item], now="2026-11-13T10:00:00Z")
        self.assertIn("date_publication_inconnue:-5", result["results"][0]["ranking_reasons"])

    def test_sorting_is_deterministic_and_duplicates_are_removed(self):
        first = candidate("lead-b")
        second = candidate("lead-a")
        duplicate = dict(first, candidate_id="lead-copy", title="Copy",
                         source_url="https://example.org/task/lead-b?utm_campaign=x")
        result = rank_global_work_opportunities(
            [first, second, duplicate], now="2026-11-13T10:00:00Z"
        )
        self.assertEqual(result["duplicate_count"], 1)
        self.assertEqual([x["candidate_id"] for x in result["results"]], ["lead-a", "lead-b"])
        self.assertEqual([x["rank"] for x in result["results"]], [1, 2])

    def test_invalid_registry_is_rejected(self):
        with self.assertRaises(ValueError):
            rank_global_work_opportunities(
                [candidate()], now="2026-11-13T10:00:00Z", source_registry={"sources": "bad"}
            )


if __name__ == "__main__":
    unittest.main()
