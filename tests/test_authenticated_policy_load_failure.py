"""Regression: policy loading failures happen after cryptographic authentication."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from papi_core.authz import (
    AccessDenied,
    AuthenticatedAuthorizationDenied,
    authorize_authenticated_agent,
)
from papi_core.identity import provision_agent_key, sign_request


class AuthenticatedPolicyLoadFailureTests(unittest.TestCase):
    def test_policy_load_failure_keeps_authenticated_principal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agents_path = root / "agents.json"
            agents_path.write_text(
                '{"agents":[{"id":"agent-a","name":"Agent A","status":"active",'
                '"permissions":["read_reports"],"prohibited":[]}]}',
                encoding="utf-8",
            )
            keys = root / "keys"
            provision_agent_key("agent-a", keys)
            envelope = sign_request(
                "agent-a",
                {"permission":"read_reports","task_id":"task-1","handler":"report.preview"},
                keys,
                nonce="policy-load-failure-0001",
            )
            with patch("papi_core.authz.load_policy",
                       side_effect=AccessDenied("policy file unavailable")):
                with self.assertRaises(AuthenticatedAuthorizationDenied) as caught:
                    authorize_authenticated_agent(
                        "agent-a", "read_reports", envelope,
                        task_id="task-1", handler="report.preview",
                        agents_path=agents_path, key_dir=keys,
                        replay_db=root / "replay.sqlite3",
                    )
            self.assertEqual(caught.exception.principal.agent_id, "agent-a")
            self.assertIsInstance(caught.exception, AccessDenied)


if __name__ == "__main__":
    unittest.main()
