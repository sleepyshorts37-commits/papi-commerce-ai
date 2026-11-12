import unittest

from runtime.papi_core.automation_coordination import coordinate_department_plans


class AutomationCoordinationTests(unittest.TestCase):
    def test_merges_tasks_from_departments(self):
        result = coordinate_department_plans({
            "PAPI SERVICES": [{"task_type": "review_case", "title": "Review case",
                               "details": {"case_ref": "C-1"}}],
            "PAPI MARKET": [{"task_type": "review_stock", "title": "Review stock",
                             "reference": "SKU-1"}],
        })
        self.assertEqual(result["summary"]["total_unique"], 2)

    def test_duplicate_department_task_is_removed(self):
        task = {"task_type": "followup", "title": "Review follow-up",
                "details": {"prospect_ref": "P-1"}}
        result = coordinate_department_plans({"PAPI SERVICES": [task, task]})
        self.assertEqual(result["summary"]["duplicates_removed"], 1)
        self.assertEqual(result["summary"]["total_unique"], 1)

    def test_same_reference_in_two_departments_remains_separate(self):
        task = {"task_type": "review", "title": "Review", "reference": "R-1"}
        result = coordinate_department_plans({"A": [task], "B": [task]})
        self.assertEqual(result["summary"]["total_unique"], 2)

    def test_missing_dependency_blocks_task(self):
        task = {"task_type": "deliver", "title": "Prepare delivery",
                "reference": "D-1", "depends_on": ["TASK-QUOTE"]}
        result = coordinate_department_plans({"PAPI SERVICES": [task]})
        self.assertEqual(result["tasks"][0]["state"], "blocked")
        self.assertEqual(result["summary"]["blocked"], 1)

    def test_completed_dependency_unblocks_for_approval_only(self):
        task = {"task_type": "deliver", "title": "Prepare delivery",
                "reference": "D-1", "depends_on": ["TASK-QUOTE"]}
        result = coordinate_department_plans(
            {"PAPI SERVICES": [task]}, completed_task_ids=["TASK-QUOTE"])
        self.assertEqual(result["tasks"][0]["state"], "awaiting_approval")
        self.assertTrue(result["tasks"][0]["requires_human_approval"])

    def test_invalid_tasks_are_rejected(self):
        result = coordinate_department_plans({"PAPI SERVICES": [
            {"title": "No task type"},
            {"task_type": "bad", "title": "Bad priority", "priority": "extreme"},
        ]})
        self.assertEqual(result["summary"]["rejected_invalid"], 2)

    def test_no_external_execution(self):
        result = coordinate_department_plans({})
        self.assertFalse(result["execution_enabled"])
        self.assertEqual(result["budget_xof"], 0)
        self.assertEqual(result["summary"]["external_actions"], 0)


if __name__ == "__main__":
    unittest.main()
