import json
import tempfile
import unittest
from pathlib import Path

from papi_core.authz import AccessDenied, authorize_agent


class AgentAccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "agents.json"
        self.agents = {"project": "PAPI COMMERCE AI", "agents": [
            {"id": "agent-a", "name": "Agent A", "status": "active",
             "permissions": ["read_reports", "send_email"],
             "prohibited": ["send_email"]},
            {"id": "agent-b", "name": "Agent B", "status": "planned",
             "permissions": ["read_reports"], "prohibited": []}
        ]}
        self.write()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self):
        self.path.write_text(json.dumps(self.agents), encoding="utf-8")

    def test_active_agent_can_use_declared_permission(self):
        result = authorize_agent("agent-a", "read_reports", self.path)
        self.assertTrue(result["authorized"])
        self.assertFalse(result["identity_authenticated"])

    def test_planned_agent_is_denied(self):
        with self.assertRaises(AccessDenied):
            authorize_agent("agent-b", "read_reports", self.path)

    def test_missing_permission_is_denied(self):
        with self.assertRaises(AccessDenied):
            authorize_agent("agent-a", "delete_data", self.path)

    def test_explicit_prohibition_overrides_permission(self):
        with self.assertRaises(AccessDenied):
            authorize_agent("agent-a", "send_email", self.path)

    def test_owner_only_action_is_denied_to_agents(self):
        self.agents["agents"][0]["permissions"].append("spend_money")
        self.write()
        with self.assertRaises(AccessDenied):
            authorize_agent("agent-a", "spend_money", self.path)

    def test_external_action_is_denied_by_policy(self):
        self.agents["agents"][0]["permissions"].append("send_message")
        self.write()
        with self.assertRaises(AccessDenied):
            authorize_agent("agent-a", "send_message", self.path,
                            {"external_actions_enabled": False})

    def test_unknown_agent_and_blank_identity_are_denied(self):
        for agent_id in ("unknown", ""):
            with self.assertRaises(AccessDenied):
                authorize_agent(agent_id, "read_reports", self.path)


if __name__ == "__main__":
    unittest.main()
