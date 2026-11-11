import json
import tempfile
import unittest
from pathlib import Path

from papi_core.command_center import build_command_center


class CommandCenterTests(unittest.TestCase):
    def test_dashboard_aggregates_metrics_without_enabling_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agents, tasks, policy = root / "agents.json", root / "tasks.json", root / "policy.json"
            agents.write_text(json.dumps({"agents": [
                {"id": "astou", "name": "Astou", "status": "defined"},
                {"id": "mariama", "name": "Mariama", "status": "planned"}
            ]}), encoding="utf-8")
            tasks.write_text(json.dumps({"tasks": [
                {"id": "T-1", "title": "Audit", "status": "ready",
                 "approval_required": True, "approval_status": "pending", "owner_agent": "astou"},
                {"id": "T-2", "title": "Research", "status": "backlog",
                 "approval_required": False, "owner_agent": "unknown"}
            ]}), encoding="utf-8")
            policy.write_text(json.dumps({
                "execution_enabled": False, "external_actions_enabled": False
            }), encoding="utf-8")
            result = build_command_center(tasks, agents, policy, {})
        dashboard = result["dashboard"]
        self.assertEqual(dashboard["agents_total"], 2)
        self.assertEqual(dashboard["tasks_total"], 2)
        self.assertEqual(dashboard["open_tasks"], 2)
        self.assertEqual(dashboard["pending_approvals"], 1)
        self.assertEqual(dashboard["unassigned_open_tasks"], 1)
        self.assertEqual(result["mode"], "read_only_local")
        self.assertFalse(result["controls"]["worker_started"])
        self.assertFalse(result["controls"]["external_actions_enabled"])
        self.assertFalse(result["environment"]["secrets_displayed"])

    def test_invalid_task_collection_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agents, tasks = root / "agents.json", root / "tasks.json"
            agents.write_text(json.dumps({"agents": [{"id": "astou", "name": "Astou"}]}), encoding="utf-8")
            tasks.write_text(json.dumps({"tasks": None}), encoding="utf-8")
            with self.assertRaises(ValueError):
                build_command_center(tasks, agents)


if __name__ == "__main__":
    unittest.main()
