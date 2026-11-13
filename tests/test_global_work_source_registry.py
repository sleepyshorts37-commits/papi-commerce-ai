import unittest

from papi_core.global_work_source_registry import (
    SourceRegistryError, validate_source_record, validate_source_registry,
)


def source(**overrides):
    value = {
        "source_id": "platform.alpha",
        "name": "Example platform",
        "source_type": "freelance_marketplace",
        "url": "https://example.org",
        "access_mode": "manual",
        "verification_status": "unverified",
        "eligible_countries": [],
        "payout_methods": [],
        "enabled": False,
    }
    value.update(overrides)
    return value


class GlobalWorkSourceRegistryTests(unittest.TestCase):
    def test_unverified_source_never_activates(self):
        result = validate_source_record(source(enabled=True))
        self.assertFalse(result["enabled"])
        self.assertFalse(result["ingestion_allowed"])
        self.assertTrue(result["human_review_required"])

    def test_verified_source_requires_independent_evidence(self):
        with self.assertRaises(SourceRegistryError):
            validate_source_record(source(verification_status="verified", enabled=True))

    def test_verified_source_with_evidence_can_be_enabled_but_not_fetched(self):
        result = validate_source_record(source(
            verification_status="verified", enabled=True, access_mode="authorized_api",
            eligible_countries=["SN"], payout_methods=["PayPal"],
            verified_at="2026-11-13T10:00:00Z", verified_by="human-reviewer",
            verification_evidence={
                "country_eligibility_url": "https://example.org/countries",
                "payout_terms_url": "https://example.org/payouts",
                "terms_url": "https://example.org/terms",
            },
        ))
        self.assertTrue(result["enabled"])
        self.assertTrue(result["ingestion_allowed"])

    def test_private_source_url_rejected(self):
        with self.assertRaises(SourceRegistryError):
            validate_source_record(source(url="https://127.0.0.1/admin"))

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(SourceRegistryError):
            validate_source_registry({"sources": [source(), source(name="Second")]})

    def test_unknown_country_and_payout_are_not_inferred(self):
        result = validate_source_registry({"sources": [source()]})
        self.assertEqual(result["sources"][0]["eligible_countries"], [])
        self.assertEqual(result["sources"][0]["payout_methods"], [])
        self.assertEqual(result["verified_count"], 0)
        self.assertFalse(result["external_actions_performed"])


if __name__ == "__main__":
    unittest.main()
