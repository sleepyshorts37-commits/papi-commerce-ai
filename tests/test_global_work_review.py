import unittest

from papi_core.global_work_review import GlobalWorkReviewError, review_global_work_opportunities


def source():
    return {
        "source_id": "source-a", "name": "Example", "source_type": "job_board",
        "url": "https://example.org", "access_mode": "manual",
        "verification_status": "verified", "eligible_countries": ["SN"],
        "payout_methods": ["PayPal"], "enabled": True,
        "verification_evidence": {
            "country_eligibility_url": "https://example.org/countries",
            "payout_terms_url": "https://example.org/payout",
            "terms_url": "https://example.org/terms",
        },
        "verified_at": "2026-11-12T10:00:00Z", "verified_by": "human-reviewer",
    }


def lead():
    return {
        "candidate_id": "lead-1", "source_id": "source-a", "title": "Remote task",
        "source_url": "https://example.org/task/1",
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


def records(countries=None):
    return [
        {"field": "eligible_countries", "url": "https://example.org/countries",
         "value": countries or ["SN"], "observed_at": "2026-11-12T10:00:00Z",
         "reviewer": "human-reviewer"},
        {"field": "payout_methods", "url": "https://example.org/payout",
         "value": ["PayPal"], "observed_at": "2026-11-12T10:00:00Z",
         "reviewer": "human-reviewer"},
    ]


class GlobalWorkReviewTests(unittest.TestCase):
    def test_unified_review_connects_registry_evidence_and_ranking(self):
        result = review_global_work_opportunities(
            [lead()], now="2026-11-13T10:00:00Z",
            source_registry={"sources": [source()]},
            evidence_records_by_source={"source-a": records()},
        )
        self.assertEqual(result["review_pipeline_version"], "unified_read_only_v1")
        self.assertEqual(result["review_summary"]["priority_for_human_review"], 1)
        self.assertEqual(result["results"][0]["ranking_status"], "priority_for_human_review")
        self.assertFalse(result["qualified"])
        self.assertFalse(result["application_submitted"])
        self.assertFalse(result["external_actions_performed"])

    def test_registry_evidence_mismatch_becomes_contradiction(self):
        result = review_global_work_opportunities(
            [lead()], now="2026-11-13T10:00:00Z",
            source_registry={"sources": [source()]},
            evidence_records_by_source={"source-a": records(["US"])},
        )
        self.assertEqual(
            result["evidence_reviews"]["source-a"]["overall_status"],
            "contradiction_detected",
        )
        self.assertIn("preuves_contradictoires", result["results"][0]["ranking_blockers"])

    def test_missing_evidence_never_counts_as_verified(self):
        result = review_global_work_opportunities(
            [lead()], now="2026-11-13T10:00:00Z",
            source_registry={"sources": [source()]},
        )
        self.assertEqual(
            result["evidence_reviews"]["source-a"]["overall_status"],
            "insufficient_evidence",
        )
        self.assertEqual(result["review_summary"]["priority_for_human_review"], 0)

    def test_evidence_for_unknown_source_is_rejected(self):
        with self.assertRaises(GlobalWorkReviewError):
            review_global_work_opportunities(
                [lead()], now="2026-11-13T10:00:00Z",
                source_registry={"sources": [source()]},
                evidence_records_by_source={"unknown": []},
            )

    def test_invalid_evidence_is_rejected(self):
        with self.assertRaises(GlobalWorkReviewError):
            review_global_work_opportunities(
                [lead()], now="2026-11-13T10:00:00Z",
                source_registry={"sources": [source()]},
                evidence_records_by_source={"source-a": [{"field": "bad"}]},
            )

    def test_no_candidates_is_safe_and_reports_sources(self):
        result = review_global_work_opportunities(
            [], now="2026-11-13T10:00:00Z",
            source_registry={"sources": [source()]},
        )
        self.assertEqual(result["results"], [])
        self.assertEqual(result["review_summary"]["hold_for_review"], 0)
        self.assertFalse(result["external_actions_performed"])


if __name__ == "__main__":
    unittest.main()
