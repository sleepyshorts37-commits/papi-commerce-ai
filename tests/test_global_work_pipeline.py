import unittest
from papi_core.global_work_pipeline import qualify_work_candidates

class GlobalWorkPipelineTests(unittest.TestCase):
    def candidate(self):
        return {
            "candidate_id": "feed:1", "source_id": "feed", "title": "Remote task",
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
    def test_complete_fresh_candidate_waits_for_human(self):
        r = qualify_work_candidates([self.candidate()], now="2026-11-13T00:00:00Z")
        self.assertEqual(r["results"][0]["pipeline_status"], "ready_for_human_review")
        self.assertFalse(r["results"][0]["qualified"])
        self.assertFalse(r["external_actions_performed"])
    def test_duplicate_candidates_collapsed(self):
        c = self.candidate()
        duplicate = dict(c, candidate_id="feed:2", title="Copy",
                         source_url="https://example.org/task/1?utm_source=newsletter")
        r = qualify_work_candidates([c, duplicate], now="2026-11-13T00:00:00Z")
        self.assertEqual(r["unique_count"], 1)
        self.assertEqual(r["duplicate_count"], 1)
    def test_stale_candidate_held(self):
        c = self.candidate(); c["published_at"] = "2026-08-01T00:00:00Z"
        r = qualify_work_candidates([c], now="2026-11-13T00:00:00Z")
        self.assertEqual(r["results"][0]["pipeline_status"], "hold_for_review")
    def test_missing_economics_held(self):
        c = self.candidate(); c.pop("eligibility")
        r = qualify_work_candidates([c], now="2026-11-13T00:00:00Z")
        self.assertEqual(r["results"][0]["economics"]["status"], "insufficient_evidence")
    def test_empty_candidates_is_safe(self):
        r = qualify_work_candidates([], now="2026-11-13T00:00:00Z")
        self.assertEqual(r["results"], [])
        self.assertFalse(r["external_actions_performed"])

if __name__ == "__main__": unittest.main()
