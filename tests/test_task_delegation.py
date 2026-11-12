import unittest

from runtime.papi_core.task_delegation import (
    TaskDelegationError, build_delegation_candidate, build_delegation_center,
)


def identity(agent_id, manager_id=None, status="active", permissions=None):
    return {
        "identity_id": f"PAPI-ID-{agent_id.upper()}", "agent_id": agent_id,
        "full_name": agent_id, "role": "Test", "department": "QA",
        "manager_id": manager_id, "mission": "Test", "competencies": [],
        "objectives": [], "autonomy_level": "none",
        "permissions": permissions or ["delegate_internal_tasks"],
        "prohibited_actions": [], "status": status,
        "created_at": "2026-01-01T00:00:00Z", "assignment_history": [],
        "evaluation_history": [], "profile_state": "complete",
    }


def fixture(sender=None, receiver=None):
    sender = sender or identity("manager")
    receiver = receiver or identity("worker", manager_id="manager")
    doc = {"identities": [sender, receiver]}
    agents = {item["agent_id"]: {"id": item["agent_id"], "status": item["status"]} for item in (sender, receiver)}
    return doc, agents


def candidate(doc, agents, **overrides):
    args = {
        "delegator_id": "manager", "assignee_id": "worker",
        "delegation_id": "DEL-001", "task_id": "TASK-001",
        "title": "Analyse marché", "instructions": "Préparer une synthèse",
        "priority": "normal", "created_at": "2026-11-12T10:00:00Z",
        "identity_document": doc, "agents": agents,
    }
    args.update(overrides)
    return build_delegation_candidate(**args)


class TaskDelegationTests(unittest.TestCase):
    def test_candidate_does_not_assign_or_notify(self):
        doc, agents = fixture()
        result = candidate(doc, agents)
        self.assertEqual(result["status"], "proposal_candidate")
        self.assertFalse(result["task_registry_modified"])
        self.assertFalse(result["assignee_notified"])

    def test_inactive_or_unpermitted_delegator_is_denied(self):
        doc, agents = fixture(sender=identity("manager", status="planned"))
        with self.assertRaises(TaskDelegationError):
            candidate(doc, agents)
        doc, agents = fixture(sender=identity("manager", permissions=["read_reports"]))
        with self.assertRaises(TaskDelegationError):
            candidate(doc, agents)

    def test_hierarchy_and_inactive_assignee_are_denied(self):
        doc, agents = fixture(receiver=identity("worker", manager_id="other"))
        with self.assertRaises(TaskDelegationError):
            candidate(doc, agents)
        doc, agents = fixture(receiver=identity("worker", manager_id="manager", status="planned"))
        with self.assertRaises(TaskDelegationError):
            candidate(doc, agents)

    def test_personal_contact_data_is_denied(self):
        doc, agents = fixture()
        with self.assertRaises(TaskDelegationError):
            candidate(doc, agents, instructions="Écrire à demo@example.com")

    def test_center_empty_is_read_only(self):
        doc, _ = fixture()
        result = build_delegation_center([], doc)
        self.assertEqual(result["proposal_count"], 0)
        self.assertEqual(result["task_assignments_executed"], 0)


if __name__ == "__main__":
    unittest.main()
