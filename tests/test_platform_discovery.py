import unittest

from papi_core.platform_discovery import (
    PlatformDiscoveryError, review_platform_candidate, review_platform_candidates,
)


def candidate(**overrides):
    value = {
        "platform_id": "market.alpha",
        "name": "Example AI marketplace",
        "url": "https://example.org",
        "discovery_query": "AI agent marketplace",
        "discovered_at": "2026-11-13T12:00:00Z",
        "discovered_by": "Aminata Diallo",
        "ai_agent_policy": "unknown",
        "senegal_eligibility": "unknown",
        "senegal_payout_status": "unknown",
        "evidence_urls": [],
        "registration_required": False,
    }
    value.update(overrides)
    return value


class PlatformDiscoveryTests(unittest.TestCase):
    def test_unknown_claims_are_never_marked_verified_or_ready(self):
        result = review_platform_candidate(candidate())
        self.assertEqual(result["status"], "needs_human_review")
        self.assertFalse(result["verified"])
        self.assertTrue(result["human_review_required"])
        self.assertIn("senegal_eligibility_unverified", result["blockers"])

    def test_registration_pauses_for_user(self):
        result = review_platform_candidate(candidate(registration_required=True))
        self.assertEqual(result["status"], "human_registration_required")
        self.assertTrue(result["requires_user_registration"])
        self.assertFalse(result["account_created"])

    def test_prohibited_ai_platform_is_rejected(self):
        result = review_platform_candidate(candidate(ai_agent_policy="prohibited"))
        self.assertEqual(result["status"], "rejected")
        self.assertIn("ai_agents_prohibited", result["blockers"])

    def test_ineligible_senegal_platform_is_rejected(self):
        result = review_platform_candidate(candidate(senegal_eligibility="ineligible"))
        self.assertEqual(result["status"], "rejected")

    def test_private_or_non_https_url_is_rejected(self):
        with self.assertRaises(PlatformDiscoveryError):
            review_platform_candidate(candidate(url="http://127.0.0.1"))

    def test_naive_timestamp_is_rejected(self):
        with self.assertRaises(PlatformDiscoveryError):
            review_platform_candidate(candidate(discovered_at="2026-11-13T12:00:00"))

    def test_duplicate_platform_ids_are_rejected(self):
        with self.assertRaises(PlatformDiscoveryError):
            review_platform_candidates([candidate(), candidate(name="Duplicate")])

    def test_batch_summary_never_performs_external_actions(self):
        result = review_platform_candidates([candidate()])
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["verified_count"], 0)
        self.assertFalse(result["external_actions_performed"])


if __name__ == "__main__":
    unittest.main()
