import unittest
from papi_core.global_work_eligibility import GlobalWorkEligibilityError, evaluate_work_opportunity

class GlobalWorkEligibilityTests(unittest.TestCase):
    def candidate(self):
        return {
            "eligible_countries": ["SN", "CI"],
            "payout": {"amount": "100", "currency": "USD", "methods": ["PayPal"]},
            "fees": "5", "upfront_cost": "0", "estimated_hours": "4",
            "kyc_required": True, "ai_policy": "allowed", "human_presence": "not_required",
            "evidence": {k: "https://example.org/" + k for k in
                         ("country_eligibility", "payout_terms", "fees", "kyc", "ai_policy")},
        }
    def test_complete_only_ready_for_human_review(self):
        r = evaluate_work_opportunity(self.candidate())
        self.assertEqual(r["status"], "ready_for_human_review")
        self.assertEqual(r["estimated_net"], "95")
        self.assertEqual(r["estimated_hourly_net"], "23.75")
        self.assertFalse(r["qualified"])
        self.assertFalse(r["application_submitted"])
    def test_missing_country_and_payment_method_remain_unknown(self):
        c = self.candidate(); c.pop("eligible_countries"); c["payout"].pop("methods")
        r = evaluate_work_opportunity(c)
        self.assertEqual(r["country_status"], "unknown")
        self.assertIn("eligible_countries", r["missing_fields"])
        self.assertIn("payout.methods", r["missing_fields"])
    def test_country_not_listed_blocks(self):
        c = self.candidate(); c["eligible_countries"] = ["US"]
        self.assertIn("applicant_country_not_listed", evaluate_work_opportunity(c)["blockers"])
    def test_ai_prohibited_blocks(self):
        c = self.candidate(); c["ai_policy"] = "prohibited"
        self.assertIn("ai_use_prohibited", evaluate_work_opportunity(c)["blockers"])
    def test_negative_net_blocks(self):
        c = self.candidate(); c["fees"] = "110"
        self.assertIn("negative_net_payout", evaluate_work_opportunity(c)["blockers"])
    def test_invalid_money_rejected(self):
        c = self.candidate(); c["fees"] = "-1"
        with self.assertRaises(GlobalWorkEligibilityError): evaluate_work_opportunity(c)

if __name__ == "__main__": unittest.main()
