import unittest

from papi_core.supervision import SupervisionError, supervise_tasks


class SupervisionTests(unittest.TestCase):
    def setUp(self):
        self.agents = {"a": {"id": "a", "name": "Agent A"}}
        self.tasks = [
            {"id": "T-critical", "title": "Mission critique", "owner_agent": "a",
             "status": "blocked", "priority": "urgent",
             "due_at": "2026-11-10T00:00:00Z",
             "updated_at": "2026-11-01T00:00:00Z",
             "approval_required": True, "approval_status": "pending"},
            {"id": "T-soon", "owner_agent": "a", "status": "in_progress",
             "priority": "normal", "due_at": "2026-11-12T12:00:00Z"},
            {"id": "T-ok", "owner_agent": "a", "status": "ready", "priority": "low"},
            {"id": "T-done", "owner_agent": None, "status": "done", "priority": "urgent"},
        ]

    def test_detects_and_ranks_risk_factors(self):
        result = supervise_tasks(
            self.tasks, agents=self.agents, as_of="2026-11-12T08:00:00Z",
            due_soon_hours=24, stale_after_hours=48,
        )
        self.assertEqual(result["risks"][0]["task_id"], "T-critical")
        self.assertEqual(result["risks"][0]["severity"], "critical")
        self.assertEqual(result["risks"][1]["task_id"], "T-soon")
        self.assertEqual(result["risks"][1]["severity"], "medium")
        self.assertEqual(result["summary"]["terminal_tasks_ignored"], 1)

    def test_missing_dates_do_not_create_staleness_alert(self):
        result = supervise_tasks(
            [{"id": "T1", "owner_agent": "a", "status": "ready", "priority": "low"}],
            agents=self.agents, as_of="2026-11-12T08:00:00Z",
        )
        self.assertEqual(result["risks"], [])

    def test_rejects_duplicate_ids(self):
        with self.assertRaises(SupervisionError):
            supervise_tasks(
                [self.tasks[0], self.tasks[0]], agents=self.agents,
                as_of="2026-11-12T08:00:00Z",
            )

    def test_rejects_naive_dates(self):
        with self.assertRaises(SupervisionError):
            supervise_tasks(
                [{"id": "T1", "owner_agent": "a", "status": "ready",
                  "priority": "low", "due_at": "2026-11-12T09:00:00"}],
                agents=self.agents, as_of="2026-11-12T08:00:00Z",
            )

    def test_rejects_invalid_thresholds(self):
        with self.assertRaises(SupervisionError):
            supervise_tasks(self.tasks, agents=self.agents,
                            as_of="2026-11-12T08:00:00Z", stale_after_hours=0)

    def test_does_not_mutate_tasks(self):
        before = [dict(task) for task in self.tasks]
        supervise_tasks(self.tasks, agents=self.agents, as_of="2026-11-12T08:00:00Z")
        self.assertEqual(self.tasks, before)


if __name__ == "__main__":
    unittest.main()
