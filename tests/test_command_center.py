import json
import tempfile
import unittest
from pathlib import Path

from papi_core.command_center import build_command_center


class CommandCenterTests(unittest.TestCase):
    def _fixtures(self, root):
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
        return tasks, agents, policy

    def test_dashboard_aggregates_metrics_without_enabling_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            tasks, agents, policy = self._fixtures(Path(directory))
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
        self.assertEqual(result["ai_workers"]["platforms"]["total"], 0)

    def test_workers_report_is_integrated_as_read_only_data(self):
        with tempfile.TemporaryDirectory() as directory:
            tasks, agents, policy = self._fixtures(Path(directory))
            result = build_command_center(
                tasks, agents, policy, {},
                platform_candidates=[
                    {"platform_id": "P1", "name": "Example", "url": "https://example.org",
                     "status": "needs_human_review"}
                ],
                handoffs=[
                    {"handoff_id": "H1", "platform_name": "Example",
                     "required_user_action": "Vérifier les conditions", "status": "awaiting_user"}
                ],
                profitability_results=[
                    {"offer_id": "O1", "currency": "XOF",
                     "estimated_net_profit_after_labor": "5000.00",
                     "estimated_net_hourly_rate": "1000.00",
                     "estimated_net_margin_percent": "20.00",
                     "status": "viable_for_human_review"}
                ],
            )
        self.assertEqual(result["ai_workers"]["platforms"]["requiring_review"][0]["platform_id"], "P1")
        self.assertEqual(result["ai_workers"]["human_handoffs"]["awaiting_user_count"], 1)
        self.assertEqual(result["ai_workers"]["profitability"]["offers_for_human_review"][0]["offer_id"], "O1")
        self.assertTrue(result["ai_workers"]["governance"]["human_review_required"])
        self.assertFalse(result["controls"]["worker_started"])
        self.assertFalse(result["controls"]["notifications_sent"])
        self.assertFalse(result["controls"]["external_actions_enabled"])

    def test_invalid_task_collection_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agents, tasks = root / "agents.json", root / "tasks.json"
            agents.write_text(json.dumps({"agents": [{"id": "astou", "name": "Astou"}]}), encoding="utf-8")
            tasks.write_text(json.dumps({"tasks": None}), encoding="utf-8")
            with self.assertRaises(ValueError):
                build_command_center(tasks, agents)

    def test_invalid_workers_collection_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            tasks, agents, policy = self._fixtures(Path(directory))
            with self.assertRaises(ValueError):
                build_command_center(tasks, agents, policy, {}, handoffs={"invalid": True})


if __name__ == "__main__":
    unittest.main()
