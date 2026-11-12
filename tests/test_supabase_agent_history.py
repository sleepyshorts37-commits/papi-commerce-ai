import unittest
from unittest.mock import patch

from papi_core.storage import StoreError, SupabaseStore


def audit_event(event_id="E-1", actor="agent-a", action="task.status_changed",
                details=None, at="2026-11-10T12:00:00Z"):
    return {
        "event_id": event_id,
        "occurred_at": at,
        "actor": actor,
        "action": action,
        "entity_type": "task",
        "entity_id": "T-1",
        "details": details if details is not None else {
            "from_status": "review", "to_status": "done"
        },
    }


class SupabaseAgentHistoryTests(unittest.TestCase):
    def setUp(self):
        self.store = SupabaseStore(url="https://example.supabase.co", key="test-key")

    def test_reads_audit_events_with_deterministic_order_and_pagination(self):
        rows = [audit_event()]
        with patch.object(self.store, "_request", return_value=rows) as request:
            result = self.store.get_audit_events(limit=10, offset=20)
        self.assertEqual(result, rows)
        self.assertEqual(request.call_args.args[0], "GET")
        self.assertIn("order=occurred_at.asc,event_id.asc", request.call_args.args[1])
        self.assertIn("limit=10&offset=20", request.call_args.args[1])

    def test_rejects_invalid_page_bounds(self):
        for kwargs in ({"limit": 0}, {"limit": 1001}, {"limit": True}, {"offset": -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(StoreError):
                self.store.get_audit_events(**kwargs)

    def test_rejects_invalid_rows(self):
        with patch.object(self.store, "_request", return_value=[{"event_id": "bad"}]):
            with self.assertRaises(StoreError):
                self.store.get_audit_events()

    def test_builds_history_from_supabase_events(self):
        rows = [audit_event()]
        with patch.object(self.store, "get_audit_events", side_effect=[rows, []]) as reader:
            result = self.store.get_agent_history(
                "agent-a", [{"id": "T-1", "created_at": "2026-11-10T10:00:00Z"}],
                page_size=10, max_pages=3, as_of="2026-11-11T00:00:00Z",
            )
        self.assertEqual(result["metrics"]["tasks_completed_by_agent"], 1)
        self.assertEqual(result["metrics"]["average_completion_seconds"], 7200.0)
        self.assertEqual(reader.call_count, 2)
        self.assertTrue(result["read_only"])

    def test_refuses_to_return_silently_truncated_history(self):
        full_page = [audit_event(event_id=f"E-{i}") for i in range(2)]
        with patch.object(self.store, "get_audit_events", return_value=full_page):
            with self.assertRaises(StoreError):
                self.store.get_agent_history("agent-a", [], page_size=2, max_pages=1)

    def test_history_rejects_duplicate_events(self):
        row = audit_event()
        with patch.object(self.store, "get_audit_events", side_effect=[[row, row], []]):
            with self.assertRaises(StoreError):
                self.store.get_agent_history("agent-a", [], page_size=2, max_pages=3)


if __name__ == "__main__":
    unittest.main()
