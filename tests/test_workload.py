import unittest

from papi_core.workload import WorkloadError, analyze_workload


class WorkloadTests(unittest.TestCase):
    def setUp(self):
        self.agents = {
            "a": {"id": "a", "name": "Agent A", "status": "active"},
            "b": {"id": "b", "name": "Agent B", "status": "planned"},
        }
        self.tasks = [
            {"id": "T1", "owner_agent": "a", "status": "in_progress",
             "priority": "high", "due_at": "2026-11-10T12:00:00Z"},
            {"id": "T2", "owner_agent": "a", "status": "blocked",
             "priority": "urgent"},
            {"id": "T3", "owner_agent": "missing", "status": "ready",
             "priority": "normal"},
            {"id": "T4", "owner_agent": "b", "status": "done",
             "priority": "low"},
        ]

    def test_reports_overdue_blocked_unassigned_and_capacity(self):
        result = analyze_workload(
            self.tasks, agents=self.agents, as_of="2026-11-12T08:00:00Z",
            capacity_by_agent={"a": 1, "b": 2},
        )
        self.assertEqual(result["summary"]["open_tasks"], 3)
        self.assertEqual(result["summary"]["overdue_count"], 1)
        self.assertEqual(result["summary"]["blocked_count"], 1)
        self.assertEqual(result["unassigned_tasks"], ["T3"])
        self.assertEqual(result["agents"]["a"]["open_tasks"], 2)
        self.assertEqual(result["agents"]["a"]["capacity_state"], "over_capacity")
        self.assertTrue(result["agents"]["a"]["redistribution_recommended"])

    def test_unknown_capacity_is_not_guessed(self):
        result = analyze_workload(
            self.tasks, agents=self.agents, as_of="2026-11-12T08:00:00Z"
        )
        self.assertIsNone(result["agents"]["a"]["capacity"])
        self.assertEqual(result["agents"]["a"]["capacity_state"], "unknown")
        self.assertFalse(result["agents"]["a"]["redistribution_recommended"])

    def test_completed_tasks_are_excluded(self):
        result = analyze_workload(
            self.tasks, agents=self.agents, as_of="2026-11-12T08:00:00Z"
        )
        self.assertNotIn("T4", result["unassigned_tasks"])
        self.assertEqual(result["agents"]["b"]["open_tasks"], 0)

    def test_rejects_naive_timestamp(self):
        with self.assertRaises(WorkloadError):
            analyze_workload(self.tasks, agents=self.agents, as_of="2026-11-12T08:00:00")

    def test_rejects_invalid_capacity(self):
        with self.assertRaises(WorkloadError):
            analyze_workload(
                self.tasks, agents=self.agents, as_of="2026-11-12T08:00:00Z",
                capacity_by_agent={"a": True},
            )

    def test_does_not_mutate_inputs(self):
        before = [dict(task) for task in self.tasks]
        analyze_workload(self.tasks, agents=self.agents, as_of="2026-11-12T08:00:00Z")
        self.assertEqual(self.tasks, before)


if __name__ == "__main__":
    unittest.main()
