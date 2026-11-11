import unittest
from pathlib import Path
from papi_core.registry import load_agents, validate_task, validate_registries

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


if __name__ == "__main__":
    unittest.main()
