import unittest

from papi_core.global_work_evidence import EvidenceReviewError, review_source_evidence


def evidence(field="eligible_countries", value=None, **overrides):
    item = {
        "field": field,
        "url": "https://example.org/eligibility",
        "value": value if value is not None else ["SN"],
        "observed_at": "2026-11-12T12:00:00Z",
        "reviewer": "human-reviewer",
    }
    item.update(overrides)
    return item


class GlobalWorkEvidenceTests(unittest.TestCase):
    def test_recent_consistent_evidence_still_requires_human_review(self):
        result = review_source_evidence(
            [evidence(), evidence(url="https://example.org/terms")],
            now="2026-11-13T12:00:00Z",
        )
        self.assertEqual(result["overall_status"], "human_review_required")
        self.assertFalse(result["verified"])
        self.assertFalse(result["external_actions_performed"])

    def test_conflicting_observations_are_flagged(self):
        result = review_source_evidence(
            [evidence(value=["SN"]), evidence(value=["US"], url="https://example.org/countries")],
            now="2026-11-13T12:00:00Z",
        )
        self.assertEqual(result["overall_status"], "contradiction_detected")
        self.assertEqual(result["contradicted_fields"], ["eligible_countries"])

    def test_stale_evidence_is_unresolved(self):
        result = review_source_evidence(
            [evidence(observed_at="2026-01-01T00:00:00Z")],
            now="2026-11-13T12:00:00Z",
        )
        self.assertEqual(result["overall_status"], "insufficient_evidence")
        self.assertEqual(result["unresolved_fields"], ["eligible_countries"])

    def test_future_evidence_is_unresolved(self):
        result = review_source_evidence(
            [evidence(observed_at="2026-11-14T00:00:00Z")],
            now="2026-11-13T12:00:00Z",
        )
        self.assertEqual(result["unresolved_fields"], ["eligible_countries"])

    def test_private_evidence_url_rejected(self):
        with self.assertRaises(EvidenceReviewError):
            review_source_evidence(
                [evidence(url="https://127.0.0.1/private")],
                now="2026-11-13T12:00:00Z",
            )

    def test_missing_human_reviewer_rejected(self):
        with self.assertRaises(EvidenceReviewError):
            review_source_evidence(
                [evidence(reviewer="")],
                now="2026-11-13T12:00:00Z",
            )

    def test_empty_evidence_is_not_verified(self):
        result = review_source_evidence([], now="2026-11-13T12:00:00Z")
        self.assertEqual(result["overall_status"], "insufficient_evidence")
        self.assertFalse(result["verified"])


if __name__ == "__main__":
    unittest.main()
