import unittest
from runtime.papi_core.automation_engine import build_automation_plan, approve_task


class AutomationEngineTests(unittest.TestCase):
    def test_daily_qualification_is_proposed_not_executed(self):
        plan = build_automation_plan(now="2026-11-12T10:00:00Z")
        self.assertEqual(plan["summary"]["total"], 1)
        self.assertEqual(plan["tasks"][0]["task_type"], "qualify_prospects")
        self.assertEqual(plan["tasks"][0]["state"], "awaiting_approval")
        self.assertFalse(plan["execution_enabled"])

    def test_overdue_followup_is_flagged(self):
        plan = build_automation_plan(
            now="2026-11-12T10:00:00Z",
            prospects=[{"prospect_ref": "P-1", "status": "qualified",
                        "next_followup_at": "2026-11-11T10:00:00Z"}],
            include_daily_qualification=False,
        )
        self.assertEqual(plan["tasks"][0]["task_type"], "overdue_followups")
        self.assertEqual(plan["tasks"][0]["priority"], "high")

    def test_active_sales_statuses_are_not_ignored(self):
        for status in ("contacted", "interested", "quote_prepared", "contact_approved"):
            with self.subTest(status=status):
                plan = build_automation_plan(
                    now="2026-11-12T10:00:00Z",
                    prospects=[{"prospect_ref": "P-9", "status": status,
                                "next_followup_at": "2026-11-11T10:00:00Z"}],
                    include_daily_qualification=False,
                )
                self.assertEqual(plan["summary"]["total"], 1)

    def test_unresolved_case_is_flagged(self):
        plan = build_automation_plan(
            now="2026-11-12T10:00:00Z",
            client_cases=[{"case_ref": "C-1", "status": "unresolved", "priority": "high"}],
            include_daily_qualification=False,
        )
        self.assertEqual(plan["tasks"][0]["task_type"], "unresolved_client_cases")

    def test_weekly_report_is_optional(self):
        plan = build_automation_plan(
            now="2026-11-12T10:00:00Z", include_daily_qualification=False,
            include_weekly_report=True,
        )
        self.assertEqual(plan["tasks"][0]["task_type"], "weekly_commercial_report")

    def test_invalid_datetime_rejected(self):
        with self.assertRaises(ValueError):
            build_automation_plan(now="not-a-date")

    def test_no_personal_contact_fields_are_emitted(self):
        plan = build_automation_plan(
            now="2026-11-12T10:00:00Z",
            prospects=[{"prospect_ref": "P-2", "status": "qualified",
                        "next_followup_at": "2026-11-11T10:00:00Z"}],
        )
        self.assertNotIn("email", str(plan).lower())
        self.assertNotIn("phone", str(plan).lower())

    def test_approval_does_not_execute(self):
        with self.assertRaises(PermissionError):
            approve_task({"tasks": []}, 0)


if __name__ == "__main__":
    unittest.main()
