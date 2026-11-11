import json
import tempfile
import unittest
from pathlib import Path

from papi_core.authz import AccessDenied, authorize_agent, authorize_authenticated_agent
from papi_core.identity import provision_agent_key, sign_request
from papi_core.identity_ed25519 import provision_ed25519_agent, sign_ed25519_request


class AgentAccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root / "agents.json"
        self.keys = self.root / "keys"
        self.db = self.root / "replay.sqlite3"
        self.agents = {"project": "PAPI COMMERCE AI", "agents": [
            {"id": "agent-a", "name": "Agent A", "status": "active",
             "permissions": ["read_reports", "send_email"], "prohibited": ["send_email"]},
            {"id": "agent-b", "name": "Agent B", "status": "planned",
             "permissions": ["read_reports"], "prohibited": []}
        ]}
        self.policy = {"external_actions_enabled": False, "action_permissions": {
            "financial": {"enabled": False}, "legal": {"enabled": False}}}
        self.write()
        self.key = provision_agent_key("agent-a", self.keys)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self):
        self.path.write_text(json.dumps(self.agents), encoding="utf-8")

    def test_active_agent_can_use_declared_permission(self):
        result = authorize_agent("agent-a", "read_reports", self.path, self.policy)
        self.assertTrue(result["authorized"])
        self.assertFalse(result["identity_authenticated"])

    def test_planned_agent_is_denied(self):
        with self.assertRaises(AccessDenied):
            authorize_agent("agent-b", "read_reports", self.path, self.policy)

    def test_missing_permission_is_denied(self):
        with self.assertRaises(AccessDenied):
            authorize_agent("agent-a", "delete_data", self.path, self.policy)

    def test_explicit_prohibition_overrides_permission(self):
        with self.assertRaises(AccessDenied):
            authorize_agent("agent-a", "send_email", self.path, self.policy)

    def test_owner_only_action_is_denied_to_agents(self):
        self.agents["agents"][0]["permissions"].append("spend_money")
        self.write()
        with self.assertRaises(AccessDenied):
            authorize_agent("agent-a", "spend_money", self.path, self.policy)

    def test_external_action_is_denied_by_policy(self):
        self.agents["agents"][0]["permissions"].append("send_message")
        self.write()
        with self.assertRaises(AccessDenied):
            authorize_agent("agent-a", "send_message", self.path, self.policy)

    def test_unknown_agent_and_blank_identity_are_denied(self):
        for agent_id in ("unknown", ""):
            with self.assertRaises(AccessDenied):
                authorize_agent(agent_id, "read_reports", self.path, self.policy)

    def signed(self, payload=None, nonce="n" * 16):
        return sign_request("agent-a", payload or {
            "permission": "read_reports", "task_id": "task-1", "handler": "report.preview"
        }, self.key, nonce=nonce)

    def test_authenticated_authorization_requires_valid_signature(self):
        result = authorize_authenticated_agent("agent-a", "read_reports", self.signed(),
            task_id="task-1", handler="report.preview", agents_path=self.path,
            policy=self.policy, key_dir=self.keys, replay_db=self.db)
        self.assertTrue(result["identity_authenticated"])
        self.assertTrue(result["replay_protected"])

    def test_identity_must_be_bound_to_job_and_permission(self):
        envelope = self.signed({"permission": "read_reports", "task_id": "other", "handler": "report.preview"})
        with self.assertRaises(AccessDenied):
            authorize_authenticated_agent("agent-a", "read_reports", envelope,
                task_id="task-1", handler="report.preview", agents_path=self.path,
                policy=self.policy, key_dir=self.keys, replay_db=self.db)

    def test_missing_signature_is_denied(self):
        with self.assertRaises(AccessDenied):
            authorize_authenticated_agent("agent-a", "read_reports", None,
                task_id="task-1", handler="report.preview", agents_path=self.path,
                policy=self.policy, key_dir=self.keys, replay_db=self.db)

    def test_replayed_identity_is_denied(self):
        envelope = self.signed(nonce="r" * 16)
        kwargs = dict(task_id="task-1", handler="report.preview", agents_path=self.path,
                      policy=self.policy, key_dir=self.keys, replay_db=self.db)
        authorize_authenticated_agent("agent-a", "read_reports", envelope, **kwargs)
        with self.assertRaises(AccessDenied):
            authorize_authenticated_agent("agent-a", "read_reports", envelope, **kwargs)

    def test_ed25519_identity_is_accepted_by_authenticated_authorizer(self):
        private_dir = self.root / "ed-private"
        public_registry = self.root / "public-keys.json"
        private = provision_ed25519_agent("agent-a", private_dir, public_registry)
        envelope = sign_ed25519_request("agent-a", {
            "permission": "read_reports", "task_id": "task-1", "handler": "report.preview"
        }, private, nonce="z" * 16)
        result = authorize_authenticated_agent("agent-a", "read_reports", envelope,
            task_id="task-1", handler="report.preview", agents_path=self.path,
            policy=self.policy, replay_db=self.root / "ed-replay.sqlite3",
            public_registry=public_registry)
        self.assertTrue(result["identity_authenticated"])
        self.assertEqual(result["identity_algorithm"], "Ed25519")

    def test_shared_ed25519_verifier_is_used_when_injected(self):
        private = provision_ed25519_agent("agent-a", self.root / "shared-private",
                                          self.root / "shared-public.json")
        envelope = sign_ed25519_request("agent-a", {
            "permission": "read_reports", "task_id": "task-1", "handler": "report.preview"
        }, private, nonce="s" * 24)

        class SharedVerifier:
            def __init__(self):
                self.calls = 0

            def verify(self, received):
                self.calls += 1
                if received is not envelope:
                    raise ValueError("unexpected envelope")
                return {"authenticated": True, "algorithm": "Ed25519",
                        "replay_protected": True, "registry": "supabase"}

        verifier = SharedVerifier()
        result = authorize_authenticated_agent("agent-a", "read_reports", envelope,
            task_id="task-1", handler="report.preview", agents_path=self.path,
            policy=self.policy, shared_identity_verifier=verifier)
        self.assertTrue(result["identity_authenticated"])
        self.assertEqual(result["identity_algorithm"], "Ed25519")
        self.assertEqual(verifier.calls, 1)

    def test_shared_ed25519_verifier_failure_denies_authorization(self):
        private = provision_ed25519_agent("agent-a", self.root / "shared-private-fail",
                                          self.root / "shared-public-fail.json")
        envelope = sign_ed25519_request("agent-a", {
            "permission": "read_reports", "task_id": "task-1", "handler": "report.preview"
        }, private, nonce="t" * 24)

        class RejectingVerifier:
            def verify(self, received):
                raise ValueError("shared nonce rejected")

        with self.assertRaises(AccessDenied):
            authorize_authenticated_agent("agent-a", "read_reports", envelope,
                task_id="task-1", handler="report.preview", agents_path=self.path,
                policy=self.policy, shared_identity_verifier=RejectingVerifier())


if __name__ == "__main__":
    unittest.main()
