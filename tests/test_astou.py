import json
import tempfile
import unittest
from pathlib import Path

from papi_core.astou import build_director_brief


class AstouBriefTests(unittest.TestCase):
    def test_empty_project_reports_no_deployed_agents_and_safe_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agents = root / "agents.json"
            tasks = root / "tasks.json"
            policy = root / "policy.json"
            agents.write_text(json.dumps({"agents": [
                {"id": "astou", "name": "Astou", "status": "defined"}
            ]}), encoding="utf-8")
            tasks.write_text(json.dumps({"tasks": []}), encoding="utf-8")
            policy.write_text(json.dumps({
                "execution_enabled": False, "external_actions_enabled": False
            }), encoding="utf-8")
            brief = build_director_brief(tasks, agents, policy)
        self.assertEqual(brief["mode"], "deterministic_read_only")
        self.assertEqual(brief["facts"]["agent_count"], 1)
        self.assertEqual(brief["facts"]["active_agent_count"], 0)
        self.assertFalse(brief["facts"]["execution_enabled"])
        self.assertFalse(brief["facts"]["external_actions_enabled"])

    def test_pending_approval_is_escalated_and_unassigned_task_flagged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agents, tasks, policy = root / "agents.json", root / "tasks.json", root / "policy.json"
            agents.write_text(json.dumps({"agents": [
                {"id": "astou", "name": "Astou", "status": "defined"}
            ]}), encoding="utf-8")
            tasks.write_text(json.dumps({"tasks": [{
                "id": "PAPI-001", "title": "Prospection", "department": "Prospection",
                "status": "ready", "approval_required": True, "approval_status": "pending",
                "owner_agent": "unknown"
            }]}), encoding="utf-8")
            policy.write_text(json.dumps({
                "execution_enabled": False, "external_actions_enabled": False
            }), encoding="utf-8")
            brief = build_director_brief(tasks, agents, policy)
        self.assertEqual(brief["owner_escalations"][0]["task_id"], "PAPI-001")
        self.assertEqual(brief["unassigned_tasks"][0]["task_id"], "PAPI-001")
        self.assertTrue(brief["recommendations"])

    def test_invalid_tasks_collection_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agents, tasks, policy = root / "agents.json", root / "tasks.json", root / "policy.json"
            agents.write_text(json.dumps({"agents": [{"id": "astou", "name": "Astou"}]}), encoding="utf-8")
            tasks.write_text(json.dumps({"tasks": {}}), encoding="utf-8")
            policy.write_text(json.dumps({}), encoding="utf-8")
            with self.assertRaises(ValueError):
                build_director_brief(tasks, agents, policy)


if __name__ == "__main__":
    unittest.main()
