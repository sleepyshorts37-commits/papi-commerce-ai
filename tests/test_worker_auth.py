import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from papi_core.worker_auth import WorkerAuthenticationError, authenticate_worker_operation


class WorkerAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.identities = self.root / "identities.json"
        self.agents = self.root / "agents.json"
        self.identities.write_text(json.dumps({"identities": [{
            "agent_id": "worker_a", "permissions": ["worker.heartbeat"],
            "status": "active", "profile_state": "complete"
        }]}))
        self.agents.write_text(json.dumps({"agents": []}))
        self.envelope = {"agent_id": "worker_a", "payload": {
            "operation": "heartbeat", "worker_id": "worker_a",
            "job_id": "JOB-1", "lease_token": str(uuid4())
        }}

    def tearDown(self):
        self.tmp.cleanup()

    def _auth(self, envelope=None):
        with patch("papi_core.worker_auth.authenticate_agent_request",
                   return_value={"authenticated": True, "identity_verified": True}) as auth:
            result = authenticate_worker_operation(
                envelope or self.envelope, identities_path=self.identities,
                agents_path=self.agents, public_registry_path=self.root / "keys.json",
                replay_db=self.root / "replay.db",
            )
        auth.assert_called_once()
        return result

    def test_valid_request_is_bound_to_worker_job_and_token(self):
        result = self._auth()
        self.assertTrue(result["worker_authenticated"])
        self.assertEqual(result["worker_id"], "worker_a")
        self.assertEqual(result["job_id"], "JOB-1")
        self.assertTrue(result["lease_token_bound"])

    def test_worker_id_spoofing_is_rejected_before_crypto(self):
        envelope = json.loads(json.dumps(self.envelope))
        envelope["payload"]["worker_id"] = "worker_b"
        with self.assertRaises(WorkerAuthenticationError):
            self._auth(envelope)

    def test_missing_permission_fails_closed(self):
        data = json.loads(self.identities.read_text())
        data["identities"][0]["permissions"] = []
        self.identities.write_text(json.dumps(data))
        with self.assertRaises(WorkerAuthenticationError):
            self._auth()

    def test_claim_must_not_name_an_unclaimed_job(self):
        envelope = json.loads(json.dumps(self.envelope))
        envelope["payload"].update(operation="claim", job_id="JOB-1")
        with self.assertRaises(WorkerAuthenticationError):
            self._auth(envelope)

    def test_unknown_operation_is_rejected(self):
        envelope = json.loads(json.dumps(self.envelope))
        envelope["payload"]["operation"] = "shell"
        with self.assertRaises(WorkerAuthenticationError):
            self._auth(envelope)


if __name__ == "__main__":
    unittest.main()
