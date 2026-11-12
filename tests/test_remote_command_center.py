import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from papi_core.remote_command_center import build_remote_command_center
from papi_core.storage import SupabaseStore, StoreError


class RemoteCommandCenterTests(unittest.TestCase):
    def test_builds_read_only_remote_dashboard(self):
        with tempfile.TemporaryDirectory() as directory:
            agents_path = Path(directory) / "agents.json"
            agents_path.write_text(json.dumps({"agents": [
                {"id": "astou", "name": "Astou", "status": "defined"},
                {"id": "worker", "name": "Worker", "status": "planned"},
            ]}), encoding="utf-8")
            store = SupabaseStore(url="https://example.supabase.co", key="test-key")
            tasks = [
                {"id": "T-1", "status": "ready"},
                {"id": "T-2", "status": "done"},
            ]
            histories = {
                "astou": {"metrics": {"recorded_events": 1, "tasks_assigned": 1,
                    "tasks_completed_by_agent": 0, "tasks_blocked_by_agent": 0,
                    "tasks_cancelled_by_agent": 0}},
                "worker": {"metrics": {"recorded_events": 1, "tasks_assigned": 0,
                    "tasks_completed_by_agent": 1, "tasks_blocked_by_agent": 0,
                    "tasks_cancelled_by_agent": 0}},
            }
            with patch.object(store, "get_tasks", return_value=tasks) as get_tasks, \
                 patch.object(store, "get_agent_histories", return_value=histories) as get_histories:
                result = build_remote_command_center(
                    store, agents_path=agents_path, environ={}, page_size=100, max_pages=2
                )
        self.assertEqual(result["mode"], "read_only_remote")
        self.assertEqual(result["dashboard"]["tasks_total"], 2)
        self.assertEqual(result["dashboard"]["open_tasks"], 1)
        self.assertEqual(result["agent_history"]["totals"]["agents_with_activity"], 2)
        self.assertFalse(result["controls"]["writes_performed"])
        self.assertFalse(result["controls"]["worker_started"])
        get_tasks.assert_called_once_with(page_size=100, max_pages=2)
        get_histories.assert_called_once()

    def test_requires_real_supabase_store(self):
        with self.assertRaises(TypeError):
            build_remote_command_center(object())


class SupabaseTaskSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.store = SupabaseStore(url="https://example.supabase.co", key="test-key")

    def test_reads_and_validates_task_snapshot(self):
        rows = [{"id": "T-1", "task": {"id": "T-1", "status": "ready"}, "version": 2}]
        with patch.object(self.store, "_request", return_value=rows) as request:
            result = self.store.get_tasks(page_size=10, max_pages=2)
        self.assertEqual(result, [{"id": "T-1", "status": "ready"}])
        self.assertIn("order=id.asc", request.call_args.args[1])

    def test_rejects_inconsistent_task_record(self):
        rows = [{"id": "T-1", "task": {"id": "T-2"}, "version": 1}]
        with patch.object(self.store, "_request", return_value=rows):
            with self.assertRaises(StoreError):
                self.store.get_tasks()

    def test_refuses_to_silently_truncate_task_snapshot(self):
        rows = [{"id": "T-1", "task": {"id": "T-1"}, "version": 1}]
        with patch.object(self.store, "_request", return_value=rows):
            with self.assertRaises(StoreError):
                self.store.get_tasks(page_size=1, max_pages=1)


if __name__ == "__main__":
    unittest.main()
