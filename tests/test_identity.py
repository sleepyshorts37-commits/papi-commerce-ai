import tempfile
import unittest
from pathlib import Path

from papi_core.identity import IdentityError, provision_agent_key, sign_request, verify_request


class AgentIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.keys = self.root / "keys"
        self.db = self.root / "replay.sqlite3"
        self.key = provision_agent_key("agent-a", self.keys)

    def tearDown(self):
        self.tmp.cleanup()

    def test_signed_request_authenticates(self):
        envelope = sign_request("agent-a", {"action": "read"}, self.key, timestamp=1000, nonce="n" * 16)
        result = verify_request(envelope, self.keys, self.db, now=1000)
        self.assertTrue(result["authenticated"])
        self.assertTrue(result["replay_protected"])

    def test_replay_is_rejected(self):
        envelope = sign_request("agent-a", {"action": "read"}, self.key, timestamp=1000, nonce="r" * 16)
        verify_request(envelope, self.keys, self.db, now=1000)
        with self.assertRaises(IdentityError):
            verify_request(envelope, self.keys, self.db, now=1000)

    def test_tampering_is_rejected(self):
        envelope = sign_request("agent-a", {"action": "read"}, self.key, timestamp=1000, nonce="t" * 16)
        envelope["payload"]["action"] = "transfer"
        with self.assertRaises(IdentityError):
            verify_request(envelope, self.keys, self.db, now=1000)

    def test_expired_signature_is_rejected(self):
        envelope = sign_request("agent-a", {"action": "read"}, self.key, timestamp=1000, nonce="e" * 16)
        with self.assertRaises(IdentityError):
            verify_request(envelope, self.keys, self.db, now=1400)

    def test_unknown_identity_is_rejected(self):
        envelope = sign_request("agent-a", {"action": "read"}, self.key, timestamp=1000, nonce="u" * 16)
        with self.assertRaises(IdentityError):
            verify_request(envelope, self.root / "missing", self.db, now=1000)

    def test_key_is_not_overwritten(self):
        with self.assertRaises(IdentityError):
            provision_agent_key("agent-a", self.keys)


if __name__ == "__main__":
    unittest.main()
