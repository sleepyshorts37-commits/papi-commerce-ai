import unittest

from papi_core.agent_history import AgentHistoryError, summarize_agent_history


def event(event_id, at, actor, action, task_id, details):
    return {
        "event_id": event_id,
        "occurred_at": at,
        "actor": actor,
        "action": action,
        "entity_type": "task",
        "entity_id": task_id,
        "details": details,
    }


class AgentHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tasks = [{
            "id": "TASK-1",
            "created_at": "2026-11-10T10:00:00Z",
            "owner_agent": "worker",
        }]
        self.events = [
            event("E1", "2026-11-10T10:05:00Z", "manager", "task.assigned",
                  "TASK-1", {"new_assignee": "worker", "previous_assignee": ""}),
            event("E2", "2026-11-10T11:00:00Z", "worker", "task.status_changed",
                  "TASK-1", {"from_status": "ready", "to_status": "in_progress"}),
            event("E3", "2026-11-10T12:00:00Z", "worker", "task.status_changed",
                  "TASK-1", {"from_status": "review", "to_status": "done"}),
        ]

    def test_metrics_are_derived_from_events(self):
        result = summarize_agent_history(
            "worker", self.events, self.tasks, as_of="2026-11-11T00:00:00Z"
        )
        metrics = result["metrics"]
        self.assertEqual(metrics["tasks_assigned"], 1)
        self.assertEqual(metrics["tasks_completed_by_agent"], 1)
        self.assertEqual(metrics["status_transitions_by_agent"], 2)
        self.assertEqual(metrics["average_completion_seconds"], 7200.0)
        self.assertIsNone(result["evaluation"]["subjective_score"])
        self.assertTrue(result["read_only"])

    def test_future_events_are_excluded(self):
        result = summarize_agent_history(
            "worker", self.events, self.tasks, as_of="2026-11-10T11:30:00Z"
        )
        self.assertEqual(result["metrics"]["tasks_completed_by_agent"], 0)
        self.assertEqual(result["metrics"]["recorded_events"], 2)

    def test_duplicate_event_is_rejected(self):
        with self.assertRaises(AgentHistoryError):
            summarize_agent_history("worker", [self.events[0], self.events[0]], self.tasks)

    def test_naive_event_timestamp_is_rejected(self):
        invalid = dict(self.events[0], occurred_at="2026-11-10T10:05:00")
        with self.assertRaises(AgentHistoryError):
            summarize_agent_history("worker", [invalid], self.tasks)

    def test_invalid_transition_details_are_rejected(self):
        invalid = event("E4", "2026-11-10T13:00:00Z", "worker",
                        "task.status_changed", "TASK-1", {})
        with self.assertRaises(AgentHistoryError):
            summarize_agent_history("worker", [invalid], self.tasks)

    def test_input_data_is_not_mutated(self):
        original = [dict(item) for item in self.events]
        summarize_agent_history("worker", self.events, self.tasks)
        self.assertEqual(self.events, original)


if __name__ == "__main__":
    unittest.main()
