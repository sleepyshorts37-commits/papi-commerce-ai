import unittest

from runtime.papi_core.automation_integration import build_plan_from_module_snapshots


class AutomationIntegrationTests(unittest.TestCase):
    def test_adapts_sales_engine_followup_field(self):
        plan = build_plan_from_module_snapshots(
            sales_pipeline={"records": [{
                "prospect_id": "P-01", "status": "qualified",
                "next_follow_up_at": "2026-11-11T10:00:00+00:00",
            }]},
            now="2026-11-12T10:00:00Z",
            include_daily_qualification=False,
        )
        self.assertEqual(plan["tasks"][0]["task_type"], "overdue_followups")
        self.assertEqual(plan["tasks"][0]["details"]["prospect_ref"], "P-01")

    def test_adapts_client_manager_open_case_ids(self):
        plan = build_plan_from_module_snapshots(
            client_manager_snapshot={"cases": {"open_case_ids": ["CASE-7"]}},
            now="2026-11-12T10:00:00Z",
            include_daily_qualification=False,
        )
        self.assertEqual(plan["tasks"][0]["task_type"], "unresolved_client_cases")
        self.assertEqual(plan["tasks"][0]["details"]["case_ref"], "CASE-7")

    def test_combines_both_module_snapshots(self):
        plan = build_plan_from_module_snapshots(
            sales_pipeline={"records": [{
                "prospect_id": "P-02", "status": "contacted",
                "next_follow_up_at": "2026-11-11T10:00:00Z",
            }]},
            client_manager_snapshot={"cases": {"open_case_ids": ["CASE-8"]}},
            now="2026-11-12T10:00:00Z",
            include_daily_qualification=True,
        )
        self.assertEqual(plan["summary"]["total"], 3)
        self.assertTrue(plan["sources"]["snapshot_only"])

    def test_rejects_malformed_snapshot(self):
        with self.assertRaises(ValueError):
            build_plan_from_module_snapshots(
                sales_pipeline={"records": "not-a-list"},
                now="2026-11-12T10:00:00Z",
            )

    def test_empty_inputs_are_safe(self):
        plan = build_plan_from_module_snapshots(
            now="2026-11-12T10:00:00Z",
            include_daily_qualification=False,
        )
        self.assertEqual(plan["summary"]["total"], 0)
        self.assertFalse(plan["execution_enabled"])


if __name__ == "__main__":
    unittest.main()
