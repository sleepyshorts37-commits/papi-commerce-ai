import unittest
from unittest.mock import Mock

from papi_core.storage import StoreError, SupabaseStore


def identity(agent_id, role, manager_id, permissions):
    return {
        "identity_id": f"PAPI-ID-{agent_id}",
        "agent_id": agent_id,
        "full_name": agent_id.title(),
        "role": role,
        "department": "Operations",
        "manager_id": manager_id,
        "mission": "Mission de test détaillée.",
        "competencies": ["coordination"],
        "objectives": ["livrer un résultat vérifiable"],
        "autonomy_level": "bounded",
        "permissions": permissions,
        "prohibited_actions": [],
        "status": "active",
        "created_at": "2026-01-01T00:00:00Z",
        "assignment_history": [],
        "evaluation_history": [],
        "profile_state": "complete",
    }


class SupabaseTaskAssignmentTests(unittest.TestCase):
    def setUp(self):
        self.agents = {
            "manager": {"id": "manager", "name": "Manager", "status": "active",
                        "permissions": ["assign_internal_tasks"], "prohibited": []},
            "worker": {"id": "worker", "name": "Worker", "status": "active",
                       "permissions": ["read_reports"], "prohibited": []},
        }
        self.identities = {
            "schema_version": 1,
            "identities": [
                identity("manager", "Direction", "owner", ["assign_internal_tasks"]),
                identity("worker", "Analyste", "manager", ["read_reports"]),
            ],
        }
        self.task = {"id": "TASK-DB-001", "status": "ready", "owner_agent": "old"}
        self.store = object.__new__(SupabaseStore)
        self.store.get_task = Mock(return_value={"task": self.task, "version": 4})
        self.store.commit_task_change = Mock(return_value=5)

    def test_assignment_and_audit_are_sent_to_single_atomic_commit(self):
        updated, version = self.store.assign_task_and_save(
            "TASK-DB-001", assigner_id="manager", assignee_id="worker",
            agents=self.agents, identity_registry=self.identities, expected_version=4,
        )
        self.assertEqual(updated["owner_agent"], "worker")
        self.assertEqual(version, 5)
        self.store.commit_task_change.assert_called_once()
        args, kwargs = self.store.commit_task_change.call_args
        self.assertEqual(args[0]["id"], "TASK-DB-001")
        self.assertEqual(args[1]["action"], "task.assigned")
        self.assertEqual(kwargs["expected_version"], 4)

    def test_stale_version_fails_before_assignment_or_commit(self):
        with self.assertRaises(StoreError):
            self.store.assign_task_and_save(
                "TASK-DB-001", assigner_id="manager", assignee_id="worker",
                agents=self.agents, identity_registry=self.identities, expected_version=3,
            )
        self.store.commit_task_change.assert_not_called()

    def test_invalid_assignment_fails_without_commit(self):
        self.identities["identities"][1]["manager_id"] = "other-manager"
        with self.assertRaises(StoreError):
            self.store.assign_task_and_save(
                "TASK-DB-001", assigner_id="manager", assignee_id="worker",
                agents=self.agents, identity_registry=self.identities, expected_version=4,
            )
        self.store.commit_task_change.assert_not_called()

    def test_boolean_version_is_rejected(self):
        with self.assertRaises(StoreError):
            self.store.assign_task_and_save(
                "TASK-DB-001", assigner_id="manager", assignee_id="worker",
                agents=self.agents, identity_registry=self.identities, expected_version=True,
            )
        self.store.commit_task_change.assert_not_called()


if __name__ == "__main__":
    unittest.main()
