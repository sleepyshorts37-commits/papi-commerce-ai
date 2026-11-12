import unittest

from papi_core.task_assignment import TaskAssignmentError, assign_task


def card(agent_id, name, role, manager_id, permissions, prohibited):
    return {
        "identity_id": f"PAPI-ID-{agent_id}",
        "agent_id": agent_id,
        "full_name": name,
        "role": role,
        "department": "Operations",
        "manager_id": manager_id,
        "mission": "Mission de test suffisamment définie.",
        "competencies": ["coordination"],
        "objectives": ["livrer un résultat vérifiable"],
        "autonomy_level": "bounded",
        "permissions": permissions,
        "prohibited_actions": prohibited,
        "status": "active",
        "created_at": "2026-01-01T00:00:00Z",
        "assignment_history": [],
        "evaluation_history": [],
        "profile_state": "complete",
    }


class TaskAssignmentTests(unittest.TestCase):
    def setUp(self):
        self.agents = {
            "manager": {
                "id": "manager", "name": "Manager", "status": "active",
                "permissions": ["assign_internal_tasks"], "prohibited": [],
            },
            "worker": {
                "id": "worker", "name": "Worker", "status": "active",
                "permissions": ["read_reports"], "prohibited": [],
            },
        }
        self.identities = {
            "schema_version": 1,
            "identities": [
                card("manager", "Manager", "Direction", None,
                     ["assign_internal_tasks"], []),
                card("worker", "Worker", "Analyste", "manager",
                     ["read_reports"], []),
            ],
        }
        self.task = {"id": "TASK-001", "status": "ready", "owner_agent": "old"}

    def test_assigns_to_active_direct_report_and_emits_audit(self):
        updated, event = assign_task(
            self.task, assigner_id="manager", assignee_id="worker",
            agents=self.agents, identity_registry=self.identities,
        )
        self.assertEqual(updated["owner_agent"], "worker")
        self.assertEqual(event["action"], "task.assigned")
        self.assertEqual(event["entity_id"], "TASK-001")
        self.assertEqual(self.task["owner_agent"], "old")

    def test_rejects_inactive_assignee(self):
        self.agents["worker"]["status"] = "planned"
        with self.assertRaises(TaskAssignmentError):
            assign_task(self.task, assigner_id="manager", assignee_id="worker",
                        agents=self.agents, identity_registry=self.identities)

    def test_rejects_incomplete_identity(self):
        self.identities["identities"][1]["profile_state"] = "incomplete"
        with self.assertRaises(TaskAssignmentError):
            assign_task(self.task, assigner_id="manager", assignee_id="worker",
                        agents=self.agents, identity_registry=self.identities)

    def test_rejects_permission_drift(self):
        self.identities["identities"][1]["permissions"] = ["send_message"]
        with self.assertRaises(TaskAssignmentError):
            assign_task(self.task, assigner_id="manager", assignee_id="worker",
                        agents=self.agents, identity_registry=self.identities)

    def test_rejects_non_manager(self):
        self.identities["identities"][1]["manager_id"] = "someone-else"
        with self.assertRaises(TaskAssignmentError):
            assign_task(self.task, assigner_id="manager", assignee_id="worker",
                        agents=self.agents, identity_registry=self.identities)

    def test_rejects_actor_without_assignment_permission(self):
        self.agents["manager"]["permissions"] = ["read_reports"]
        self.identities["identities"][0]["permissions"] = ["read_reports"]
        with self.assertRaises(TaskAssignmentError):
            assign_task(self.task, assigner_id="manager", assignee_id="worker",
                        agents=self.agents, identity_registry=self.identities)

    def test_rejects_terminal_task(self):
        self.task["status"] = "done"
        with self.assertRaises(TaskAssignmentError):
            assign_task(self.task, assigner_id="manager", assignee_id="worker",
                        agents=self.agents, identity_registry=self.identities)


if __name__ == "__main__":
    unittest.main()
