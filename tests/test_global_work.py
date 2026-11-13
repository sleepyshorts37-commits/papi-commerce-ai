import unittest

from papi_core.global_work import (GlobalWorkError, evaluate_opportunity, validate_opportunity,\n                                   validate_global_work_registry)


def opportunity(**overrides):
    value = {
        "id": "mission-001",
        "source_url": "https://example.org/task/1",
        "title": "Data classification",
        "description": "Classify public product records.",
        "country_eligibility": "Worldwide",
        "eligible_countries": ["SN", "IN", "FR"],
        "compensation_amount": 25,
        "currency": "USD",
        "estimated_minutes": 60,
        "upfront_cost": 0,
        "automation_policy": "allowed",
        "ai_policy": "allowed",
        "human_presence_required": False,
        "payout_methods": ["PayPal"],
    }
    value.update(overrides)
    return value


class GlobalWorkTests(unittest.TestCase):
    def test_valid_zero_cost_worldwide_opportunity_is_candidate_only(self):
        result = evaluate_opportunity(opportunity(), accepted_payout_methods=("PayPal",))
        self.assertEqual(result["decision"], "candidate_for_owner_policy_review")
        self.assertFalse(result["application_submitted"])
        self.assertTrue(result["owner_approval_required_before_application"])

    def test_senegal_eligibility_is_required(self):
        result = evaluate_opportunity(
            opportunity(country_eligibility="Selected countries", eligible_countries=["IN"]),
            accepted_payout_methods=("PayPal",),
        )
        self.assertEqual(result["decision"], "manual_review")

    def test_upfront_cost_is_rejected_by_zero_cost_policy(self):
        result = evaluate_opportunity(opportunity(upfront_cost=5))
        self.assertEqual(result["decision"], "reject")

    def test_platform_prohibition_is_rejected(self):
        result = evaluate_opportunity(opportunity(automation_policy="prohibited"))
        self.assertEqual(result["decision"], "reject")

    def test_ai_prohibition_is_rejected(self):
        result = evaluate_opportunity(opportunity(ai_policy="prohibited"))
        self.assertEqual(result["decision"], "reject")

    def test_human_presence_requirement_is_rejected(self):
        result = evaluate_opportunity(opportunity(human_presence_required=True))
        self.assertEqual(result["decision"], "reject")

    def test_sensitive_fields_are_rejected(self):
        self.assertTrue(any("sensible" in error for error in validate_opportunity(
            opportunity(access_token="must-not-be-stored")
        )))

    def test_non_https_source_is_rejected(self):
        self.assertTrue(any("HTTPS" in error for error in validate_opportunity(
            opportunity(source_url="http://example.org/task")
        )))

    def test_invalid_currency_or_duration_is_rejected(self):
        self.assertTrue(validate_opportunity(opportunity(currency="", estimated_minutes=0)))

    def test_invalid_input_raises(self):
        with self.assertRaises(GlobalWorkError):
            evaluate_opportunity({"id": "incomplete"})


class GlobalWorkRegistryTests(unittest.TestCase):
    def test_empty_registry_is_valid(self):
        self.assertEqual(validate_global_work_registry({
            "project": "PAPI COMMERCE AI", "schema_version": "1.0", "owner_country": "SN",
            "priority_policy": "zero_upfront_cost", "opportunities": [], "note": "empty"
        }), [])

    def test_duplicate_opportunity_ids_are_rejected(self):
        item = {
            "id": "mission-001", "source_url": "https://example.org/task", "title": "Task",
            "description": "Task description", "country_eligibility": "Worldwide",
            "eligible_countries": ["SN"], "compensation_amount": 10, "currency": "USD",
            "estimated_minutes": 30, "upfront_cost": 0, "automation_policy": "allowed",
            "ai_policy": "allowed", "human_presence_required": False, "payout_methods": ["PayPal"]
        }
        data = {"project": "PAPI COMMERCE AI", "opportunities": [item, dict(item)]}
        self.assertTrue(any("dupliqué" in error for error in validate_global_work_registry(data)))


if __name__ == "__main__":
    unittest.main()
