import unittest

from runtime.papi_core.agent_performance import build_agent_performance


class AgentPerformanceTests(unittest.TestCase):
    def test_planned_agent_is_not_evaluated_as_zero_performance(self):
        result = build_agent_performance(
            {"demo": {"id": "demo", "name": "Demo", "status": "planned"}},
            [], [],
        )
        agent = result["by_agent"]["demo"]
        self.assertEqual(agent["evaluation_status"], "not_evaluable")
        self.assertIsNone(agent["metrics"]["completion_ratio"])
        self.assertIsNone(agent["commercial_performance"]["verified_revenue_xof"])

    def test_active_agent_with_no_history_has_insufficient_evidence(self):
        result = build_agent_performance(
            {"demo": {"id": "demo", "name": "Demo", "status": "active"}},
            [], [],
        )
        self.assertEqual(result["by_agent"]["demo"]["evaluation_status"], "insufficient_evidence")

    def test_task_events_produce_traceable_completion_metrics(self):
        tasks = [{"id": "t1", "created_at": "2026-01-01T00:00:00Z"}]
        events = [
            {"event_id": "e1", "occurred_at": "2026-01-01T00:00:01Z", "actor": "manager",
             "action": "task.assigned", "entity_type": "task", "entity_id": "t1",
             "details": {"new_assignee": "demo"}},
            {"event_id": "e2", "occurred_at": "2026-01-01T00:01:00Z", "actor": "demo",
             "action": "task.status_changed", "entity_type": "task", "entity_id": "t1",
             "details": {"from_status": "in_progress", "to_status": "done"}},
        ]
        result = build_agent_performance(
            {"demo": {"id": "demo", "name": "Demo", "status": "active"}},
            events, tasks, as_of="2026-01-02T00:00:00Z",
        )
        agent = result["by_agent"]["demo"]
        self.assertEqual(agent["evaluation_status"], "measured")
        self.assertEqual(agent["metrics"]["tasks_assigned"], 1)
        self.assertEqual(agent["metrics"]["tasks_completed_by_agent"], 1)
        self.assertEqual(agent["metrics"]["completion_ratio"], 1.0)

    def test_no_revenue_is_inferred_and_no_actions_are_performed(self):
        result = build_agent_performance(
            {"demo": {"id": "demo", "name": "Demo", "status": "planned"}},
            [], [],
        )
        self.assertFalse(result["controls"]["commercial_revenue_inferred"])
        self.assertEqual(result["controls"]["actions_executed"], 0)


if __name__ == "__main__":
    unittest.main()
