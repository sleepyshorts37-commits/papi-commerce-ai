import unittest

from papi_core.agent_governance import (
    GovernanceError, authorize_delegation, validate_hierarchy,
)


def registry():
    return {
        "director": {
            "id": "director", "status": "active", "manager_agent_id": None,
            "permissions": ["delegate_tasks", "read_reports", "prepare_reports"],
        },
        "analyst": {
            "id": "analyst", "status": "active", "manager_agent_id": "director",
            "permissions": ["read_reports", "prepare_reports"],
        },
        "inactive": {
            "id": "inactive", "status": "suspended", "manager_agent_id": "director",
            "permissions": ["read_reports"],
        },
        "other": {
            "id": "other", "status": "active", "manager_agent_id": None,
            "permissions": ["read_reports", "delegate_tasks"],
        },
    }


class HierarchyGovernanceTests(unittest.TestCase):
    def test_direct_manager_can_propose_bounded_delegation(self):
        result = authorize_delegation("director", "analyst", ["read_reports"], registry())
        self.assertEqual(result["status"], "authorized_for_review")
        self.assertEqual(result["permissions"], ["read_reports"])
        self.assertFalse(result["mutates_registry"])
        self.assertTrue(result["requires_audit"])

    def test_self_delegation_is_rejected(self):
        with self.assertRaises(GovernanceError):
            authorize_delegation("director", "director", ["read_reports"], registry())

    def test_non_manager_cannot_delegate(self):
        with self.assertRaises(GovernanceError):
            authorize_delegation("other", "analyst", ["read_reports"], registry())

    def test_inactive_delegate_is_rejected(self):
        with self.assertRaises(GovernanceError):
            authorize_delegation("director", "inactive", ["read_reports"], registry())

    def test_delegator_cannot_escalate_own_permissions(self):
        with self.assertRaises(GovernanceError):
            authorize_delegation("director", "analyst", ["transfer_funds"], registry())

    def test_delegate_permission_ceiling_is_enforced(self):
        with self.assertRaises(GovernanceError):
            authorize_delegation("director", "analyst", ["prepare_reports", "delegate_tasks"], registry())

    def test_delegator_needs_explicit_delegation_permission(self):
        agents = registry()
        agents["director"]["permissions"].remove("delegate_tasks")
        with self.assertRaises(GovernanceError):
            authorize_delegation("director", "analyst", ["read_reports"], agents)

    def test_hierarchy_cycle_is_rejected(self):
        agents = registry()
        agents["director"]["manager_agent_id"] = "analyst"
        with self.assertRaises(GovernanceError):
            validate_hierarchy(agents)

    def test_unknown_manager_is_rejected(self):
        agents = registry()
        agents["analyst"]["manager_agent_id"] = "missing"
        with self.assertRaises(GovernanceError):
            validate_hierarchy(agents)

    def test_duplicate_permissions_are_rejected(self):
        agents = registry()
        agents["analyst"]["permissions"] = ["read_reports", "read_reports"]
        with self.assertRaises(GovernanceError):
            authorize_delegation("director", "analyst", ["read_reports"], agents)


if __name__ == "__main__":
    unittest.main()
