import sqlite3
import tempfile
import unittest
from pathlib import Path

from papi_core.identity_transactions import (
    IdentityTransactionError, IdentityTransactionManager,
)


class IdentityTransactionManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "identity.sqlite3"
        self.manager = IdentityTransactionManager(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def provision(self):
        return self.manager.apply(
            agent_id="agent-a", operation="provision", idempotency_key="create-1",
            actor_id="owner", key_version=1, permissions=["read_reports"],
            prohibited=["spend_money"], approval_ref="approval-001",
        )

    def test_provision_and_read_state(self):
        event = self.provision()
        self.assertEqual(event["revision"], 1)
        state = self.manager.get_state("agent-a")
        self.assertEqual(state["status"], "active")
        self.assertEqual(state["permissions"], ["read_reports"])
        self.assertEqual(state["prohibited"], ["spend_money"])

    def test_idempotent_replay_does_not_duplicate_event(self):
        first = self.provision()
        replay = self.provision()
        self.assertEqual(first["transaction_id"], replay["transaction_id"])
        self.assertTrue(replay["idempotent_replay"])
        self.assertEqual(self.manager.verify_event_chain()["events"], 1)

    def test_idempotency_key_cannot_be_reused_for_different_request(self):
        self.provision()
        with self.assertRaises(IdentityTransactionError):
            self.manager.apply(
                agent_id="agent-a", operation="revoke", idempotency_key="create-1",
                actor_id="owner", expected_revision=1, approval_ref="approval-002",
            )

    def test_rotation_requires_exact_next_key_version(self):
        self.provision()
        with self.assertRaises(IdentityTransactionError):
            self.manager.apply(
                agent_id="agent-a", operation="rotate", idempotency_key="rotate-1",
                actor_id="owner", expected_revision=1, key_version=3,
                approval_ref="approval-002",
            )
        event = self.manager.apply(
            agent_id="agent-a", operation="rotate", idempotency_key="rotate-2",
            actor_id="owner", expected_revision=1, key_version=2,
            approval_ref="approval-003",
        )
        self.assertEqual(event["revision"], 2)
        self.assertEqual(event["key_version"], 2)

    def test_permission_change_requires_approval_and_respects_denials(self):
        self.provision()
        with self.assertRaises(IdentityTransactionError):
            self.manager.apply(
                agent_id="agent-a", operation="permissions", idempotency_key="perm-1",
                actor_id="owner", expected_revision=1, permissions=["send_message"],
            )
        with self.assertRaises(IdentityTransactionError):
            self.manager.apply(
                agent_id="agent-a", operation="permissions", idempotency_key="perm-2",
                actor_id="owner", expected_revision=1,
                permissions=["spend_money"], approval_ref="approval-004",
            )

    def test_stale_revision_is_rejected(self):
        self.provision()
        self.manager.apply(
            agent_id="agent-a", operation="rotate", idempotency_key="rotate-3",
            actor_id="owner", expected_revision=1, key_version=2,
            approval_ref="approval-005",
        )
        with self.assertRaises(IdentityTransactionError):
            self.manager.apply(
                agent_id="agent-a", operation="permissions", idempotency_key="perm-3",
                actor_id="owner", expected_revision=1, permissions=["read_reports"],
                approval_ref="approval-006",
            )

    def test_revocation_is_terminal(self):
        self.provision()
        revoked = self.manager.apply(
            agent_id="agent-a", operation="revoke", idempotency_key="revoke-1",
            actor_id="owner", expected_revision=1, approval_ref="approval-007",
        )
        self.assertEqual(revoked["status"], "revoked")
        with self.assertRaises(IdentityTransactionError):
            self.manager.apply(
                agent_id="agent-a", operation="rotate", idempotency_key="rotate-after-revoke",
                actor_id="owner", expected_revision=2, key_version=2,
                approval_ref="approval-008",
            )

    def test_append_only_triggers_reject_mutation(self):
        self.provision()
        with sqlite3.connect(self.db) as connection:
            with self.assertRaises(sqlite3.DatabaseError):
                connection.execute("DELETE FROM identity_events")

    def test_hash_chain_verifies_and_detects_tampering(self):
        self.provision()
        self.manager.apply(
            agent_id="agent-a", operation="rotate", idempotency_key="rotate-4",
            actor_id="owner", expected_revision=1, key_version=2,
            approval_ref="approval-009",
        )
        self.assertTrue(self.manager.verify_event_chain()["valid"])
        with sqlite3.connect(self.db) as connection:
            connection.execute(
                "UPDATE identity_events SET event_json='{}' WHERE sequence=1"
            )
        with self.assertRaises(IdentityTransactionError):
            self.manager.verify_event_chain()

    def test_invalid_identifiers_and_conflicting_permissions_rejected(self):
        with self.assertRaises(IdentityTransactionError):
            self.manager.apply(
                agent_id="../agent", operation="provision", idempotency_key="bad-1",
                actor_id="owner", key_version=1, approval_ref="approval-010",
            )
        with self.assertRaises(IdentityTransactionError):
            self.manager.apply(
                agent_id="agent-b", operation="provision", idempotency_key="bad-2",
                actor_id="owner", key_version=1, permissions=["read"],
                prohibited=["read"], approval_ref="approval-011",
            )

    def test_database_permissions_are_private(self):
        self.provision()
        self.assertEqual(self.db.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
