import json
import tempfile
import unittest
from pathlib import Path
from papi_core.registry import load_agents, validate_task, validate_registries
from papi_core.orchestrator import build_dispatch_plan

ROOT = Path(__file__).resolve().parents[1]


class RegistryTests(unittest.TestCase):
    def test_committed_registries_are_valid(self):
        self.assertEqual(validate_registries(), [])

    def test_unknown_agent_is_rejected(self):
        task = {
            "id": "PAPI-TEST-001", "title": "Test", "department": "Test",
            "owner_agent": "agent-inexistant", "status": "backlog",
            "priority": "normal", "created_at": "2026-11-11T00:00:00Z",
            "approval_required": False
        }
        errors = validate_task(task, load_agents())
        self.assertTrue(any("Agent inconnu" in error for error in errors))

    def test_unapproved_task_cannot_start(self):
        task = {
            "id": "PAPI-TEST-002", "title": "Test", "department": "Test",
            "owner_agent": "astou", "status": "in_progress",
            "priority": "normal", "created_at": "2026-11-11T00:00:00Z",
            "approval_required": True, "approval_status": "pending"
        }
        errors = validate_task(task, load_agents())
        self.assertTrue(any("sans approbation" in error for error in errors))

    def test_done_task_requires_evidence(self):
        task = {
            "id": "PAPI-TEST-003", "title": "Test", "department": "Test",
            "owner_agent": "astou", "status": "done", "priority": "normal",
            "created_at": "2026-11-11T00:00:00Z", "approval_required": False
        }
        errors = validate_task(task, load_agents())
        self.assertTrue(any("preuve" in error for error in errors))

    def test_dispatch_plan_is_proposal_only_and_priority_sorted(self):
        with tempfile.TemporaryDirectory() as directory:
            tasks_path = Path(directory) / "tasks.json"
            tasks_path.write_text(json.dumps({"tasks": [
                {"id": "PAPI-LOW-001", "department": "Prospection", "status": "ready", "priority": "low", "created_at": "2026-11-11"},
                {"id": "PAPI-HIGH-001", "department": "Prospection", "status": "ready", "priority": "high", "created_at": "2026-11-11"}
            ]}), encoding="utf-8")
            plan = build_dispatch_plan(tasks_path)
        self.assertEqual(plan["mode"], "proposal_only")
        self.assertEqual(plan["proposals"][0]["task_id"], "PAPI-HIGH-001")
        self.assertFalse(plan["proposals"][0]["dispatch_allowed"])
        self.assertEqual(plan["proposals"][0]["blocking_reason"], "no_deployed_agent")

    def test_approval_blocks_dispatch_proposal(self):
        with tempfile.TemporaryDirectory() as directory:
            tasks_path = Path(directory) / "tasks.json"
            tasks_path.write_text(json.dumps({"tasks": [
                {"id": "PAPI-APP-001", "department": "Direction", "status": "ready", "priority": "urgent", "approval_required": True, "approval_status": "pending"}
            ]}), encoding="utf-8")
            plan = build_dispatch_plan(tasks_path)
        self.assertEqual(plan["proposals"][0]["blocking_reason"], "approval_required")
        self.assertFalse(plan["proposals"][0]["dispatch_allowed"])


if __name__ == "__main__":
    unittest.main()
