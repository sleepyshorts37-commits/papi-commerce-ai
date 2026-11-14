import unittest

from papi_core.identity_snapshot_contract import (
    IdentitySnapshotContractError,
    validate_ledger_states,
    validate_registry_agents,
)


def registry_agent(**overrides):
    item = {
        "id": "agent-a", "status": "planned",
        "permissions": ["read"], "prohibited": ["spend"],
    }
    item.update(overrides)
    return item


def ledger_state(**overrides):
    item = {
        "agent_id": "agent-a", "status": "active", "revision": 1,
        "key_version": 1, "permissions": ["read"], "prohibited": ["spend"],
    }
    item.update(overrides)
    return item


class IdentitySnapshotContractTests(unittest.TestCase):
    def test_accepts_valid_registry_and_ledger(self):
        validate_registry_agents([registry_agent()])
        validate_ledger_states([ledger_state()])

    def test_rejects_duplicate_registry_ids(self):
        with self.assertRaises(IdentitySnapshotContractError):
            validate_registry_agents([registry_agent(), registry_agent()])

    def test_rejects_invalid_agent_id(self):
        with self.assertRaises(IdentitySnapshotContractError):
            validate_registry_agents([registry_agent(id="../agent")])

    def test_rejects_duplicate_capability(self):
        with self.assertRaises(IdentitySnapshotContractError):
            validate_registry_agents([registry_agent(permissions=["read", "read"])])

    def test_rejects_permission_also_prohibited(self):
        with self.assertRaises(IdentitySnapshotContractError):
            validate_registry_agents([registry_agent(prohibited=["read"])])

    def test_rejects_non_string_capability(self):
        with self.assertRaises(IdentitySnapshotContractError):
            validate_registry_agents([registry_agent(permissions=["read", 7])])

    def test_rejects_empty_or_oversized_status(self):
        for status in (" ", "x" * 65):
            with self.subTest(status=status):
                with self.assertRaises(IdentitySnapshotContractError):
                    validate_registry_agents([registry_agent(status=status)])

    def test_rejects_duplicate_ledger_ids(self):
        with self.assertRaises(IdentitySnapshotContractError):
            validate_ledger_states([ledger_state(), ledger_state()])

    def test_rejects_boolean_revision(self):
        with self.assertRaises(IdentitySnapshotContractError):
            validate_ledger_states([ledger_state(revision=True)])

    def test_rejects_non_positive_key_version(self):
        with self.assertRaises(IdentitySnapshotContractError):
            validate_ledger_states([ledger_state(key_version=0)])

    def test_rejects_oversized_capability_list(self):
        with self.assertRaises(IdentitySnapshotContractError):
            validate_registry_agents([registry_agent(permissions=[f"p{i}" for i in range(257)])])


if __name__ == "__main__":
    unittest.main()
