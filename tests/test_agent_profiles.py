"""Regression tests for professional profiles and least-privilege delegation."""
import unittest

from papi_core.agent_profiles import resolve_effective_permissions, validate_agent_profiles


class AgentProfileTests(unittest.TestCase):
    def setUp(self):
        self.agents = {
            "director": {"id": "director", "name": "Direction", "role": "Direction", "department": "Direction", "status": "active",
                         "permissions": ["read_reports", "assign_tasks"], "prohibited": ["make_payment"]},
            "analyst": {"id": "analyst", "name": "Analyste", "role": "Recherche", "department": "Recherche", "status": "active",
                        "permissions": ["read_reports", "assign_tasks"], "prohibited": ["make_payment"]},
        }
        self.profiles = {
            "director": {
                "id": "director", "name": "Direction", "role": "Direction", "team": "Direction",
                "manager_id": None, "mission": "Superviser les missions", "skills": ["supervision"],
                "objectives": ["qualité"], "autonomy_level": "supervised",
                "permissions": ["read_reports", "assign_tasks"],
                "delegable_permissions": ["read_reports", "assign_tasks"],
                "status": "active", "history": [],
            },
            "analyst": {
                "id": "analyst", "name": "Analyste", "role": "Recherche", "team": "Recherche",
                "manager_id": "director", "mission": "Préparer des analyses", "skills": ["recherche"],
                "objectives": ["rapports fiables"], "autonomy_level": "proposal_only",
                "permissions": ["read_reports"], "delegable_permissions": [],
                "status": "active", "history": [],
            },
        }

    def test_complete_hierarchy_is_valid_and_permissions_are_intersected(self):
        self.assertEqual(validate_agent_profiles(self.profiles, self.agents), [])
        self.assertEqual(resolve_effective_permissions("analyst", self.profiles), {"read_reports"})

    def test_child_cannot_self_elevate_beyond_manager_delegation(self):
        self.profiles["analyst"]["permissions"] = ["read_reports", "assign_tasks"]
        self.profiles["director"]["delegable_permissions"] = ["read_reports"]
        errors = validate_agent_profiles(self.profiles, self.agents)
        self.assertTrue(any("permissions non déléguées" in error for error in errors))

    def test_profile_permissions_must_be_declared_in_central_agent_registry(self):
        self.profiles["director"]["permissions"] = ["read_reports", "assign_tasks", "send_message"]
        errors = validate_agent_profiles(self.profiles, self.agents)
        self.assertTrue(any("liste autorisée du registre central" in error for error in errors))

    def test_profile_cannot_grant_central_prohibited_permission(self):
        self.agents["director"]["permissions"].append("make_payment")
        self.profiles["director"]["permissions"].append("make_payment")
        errors = validate_agent_profiles(self.profiles, self.agents)
        self.assertTrue(any("permission interdite" in error for error in errors))

    def test_delegable_permissions_must_be_declared_by_profile(self):
        self.profiles["director"]["delegable_permissions"].append("send_message")
        errors = validate_agent_profiles(self.profiles, self.agents)
        self.assertTrue(any("propres permissions déclarées" in error for error in errors))

    def test_agent_cannot_be_its_own_manager(self):
        self.profiles["analyst"]["manager_id"] = "analyst"
        errors = validate_agent_profiles(self.profiles, self.agents)
        self.assertTrue(any("propre responsable" in error for error in errors))

    def test_hierarchy_cycle_is_rejected(self):
        self.profiles["director"]["manager_id"] = "analyst"
        errors = validate_agent_profiles(self.profiles, self.agents)
        self.assertTrue(any("cyclique" in error for error in errors))

    def test_suspended_manager_removes_inherited_permissions(self):
        self.profiles["director"]["status"] = "suspended"
        self.assertEqual(resolve_effective_permissions("analyst", self.profiles), set())

    def test_suspended_agent_has_no_effective_permissions(self):
        self.profiles["analyst"]["status"] = "suspended"
        self.assertEqual(resolve_effective_permissions("analyst", self.profiles), set())

    def test_profile_cannot_activate_an_agent_in_planned_registry(self):
        self.agents["analyst"]["status"] = "planned"
        errors = validate_agent_profiles(self.profiles, self.agents)
        self.assertTrue(any("activer seul" in error for error in errors))

    def test_history_requires_timezone_and_actor(self):
        self.profiles["analyst"]["history"] = [
            {"at": "2026-11-19T10:00:00", "action": "profile_created", "actor": "system"}
        ]
        errors = validate_agent_profiles(self.profiles, self.agents)
        self.assertTrue(any("fuseau horaire" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
