import unittest

from papi_core.task_routing import TaskRoutingError, recommend_assignees


def make_card(agent_id, role, department, manager_id, permissions, competencies, objectives):
    return {
        "identity_id": f"PAPI-ID-{agent_id}", "agent_id": agent_id,
        "full_name": agent_id.title(), "role": role, "department": department,
        "manager_id": manager_id, "mission": "Mission de test détaillée.",
        "competencies": competencies, "objectives": objectives,
        "autonomy_level": "bounded", "permissions": permissions,
        "prohibited_actions": [], "status": "active",
        "created_at": "2026-01-01T00:00:00Z", "assignment_history": [],
        "evaluation_history": [], "profile_state": "complete",
    }


class TaskRoutingTests(unittest.TestCase):
    def setUp(self):
        self.agents = {
            "manager": {"id": "manager", "name": "Manager", "status": "active",
                        "department": "Direction", "role": "Coordination",
                        "permissions": ["assign_internal_tasks"], "prohibited": []},
            "researcher": {"id": "researcher", "name": "Researcher", "status": "active",
                           "department": "Recherche", "role": "Étude de marché",
                           "permissions": ["research_public_sources"], "prohibited": []},
            "analyst": {"id": "analyst", "name": "Analyst", "status": "active",
                        "department": "Recherche", "role": "Analyse commerciale",
                        "permissions": ["research_public_sources"], "prohibited": []},
            "inactive": {"id": "inactive", "name": "Inactive", "status": "planned",
                         "department": "Recherche", "role": "Recherche",
                         "permissions": ["research_public_sources"], "prohibited": []},
        }
        self.identities = {"schema_version": 1, "identities": [
            make_card("manager", "Coordination", "Direction", "owner",
                      ["assign_internal_tasks"], ["gestion"], ["coordonner"]),
            make_card("researcher", "Étude de marché", "Recherche", "manager",
                      ["research_public_sources"], ["étude de marché", "demande"], ["analyse demande"]),
            make_card("analyst", "Analyse commerciale", "Recherche", "manager",
                      ["research_public_sources"], ["analyse", "données"], ["analyse commerciale"]),
            make_card("inactive", "Recherche", "Recherche", "manager",
                      ["research_public_sources"], ["étude de marché"], ["analyse demande"]),
        ]}
        self.task = {
            "id": "TASK-ROUTE-1", "title": "Étude de marché et analyse de la demande",
            "department": "Recherche", "required_permission": "research_public_sources",
        }

    def test_ranks_by_department_skills_and_workload(self):
        results = recommend_assignees(
            self.task, agents=self.agents, identity_registry=self.identities,
            workload_by_agent={"researcher": 4, "analyst": 0}, assigner_id="manager",
        )
        self.assertEqual([r["agent_id"] for r in results], ["analyst", "researcher"])
        self.assertEqual(results[0]["score"], 100)
        self.assertEqual(results[1]["score"], 92)

    def test_excludes_inactive_and_non_direct_reports(self):
        results = recommend_assignees(
            self.task, agents=self.agents, identity_registry=self.identities,
            assigner_id="another-manager",
        )
        self.assertEqual(results, [])

    def test_excludes_agent_missing_required_permission(self):
        self.task["required_permission"] = "publish_publicly"
        results = recommend_assignees(
            self.task, agents=self.agents, identity_registry=self.identities,
            assigner_id="manager",
        )
        self.assertEqual(results, [])

    def test_rejects_invalid_workload(self):
        with self.assertRaises(TaskRoutingError):
            recommend_assignees(
                self.task, agents=self.agents, identity_registry=self.identities,
                workload_by_agent={"researcher": True},
            )

    def test_does_not_mutate_inputs(self):
        before = dict(self.task)
        recommend_assignees(self.task, agents=self.agents, identity_registry=self.identities)
        self.assertEqual(self.task, before)


if __name__ == "__main__":
    unittest.main()
