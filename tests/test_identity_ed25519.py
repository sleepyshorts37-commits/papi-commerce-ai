import tempfile
import unittest
from pathlib import Path

from papi_core.identity_ed25519 import (
    Ed25519IdentityError, provision_ed25519_agent, revoke_ed25519_agent,
    rotate_ed25519_agent, sign_ed25519_request, verify_ed25519_request,
)


class Ed25519IdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.private_dir = self.root / "private"
        self.registry = self.root / "public.json"
        self.replay = self.root / "replay.sqlite3"
        self.private = provision_ed25519_agent("agent-a", self.private_dir, self.registry)

    def tearDown(self):
        self.tmp.cleanup()

    def test_sign_and_verify(self):
        envelope = sign_ed25519_request("agent-a", {"permission": "read"}, self.private,
                                        timestamp=1000, nonce="a" * 16)
        result = verify_ed25519_request(envelope, self.registry, self.replay, now=1000)
        self.assertEqual(result["algorithm"], "Ed25519")

    def test_replay_rejected(self):
        envelope = sign_ed25519_request("agent-a", {"permission": "read"}, self.private,
                                        timestamp=1000, nonce="b" * 16)
        verify_ed25519_request(envelope, self.registry, self.replay, now=1000)
        with self.assertRaises(Ed25519IdentityError):
            verify_ed25519_request(envelope, self.registry, self.replay, now=1000)

    def test_tampering_rejected(self):
        envelope = sign_ed25519_request("agent-a", {"permission": "read"}, self.private,
                                        timestamp=1000, nonce="c" * 16)
        envelope["payload"]["permission"] = "spend_money"
        with self.assertRaises(Ed25519IdentityError):
            verify_ed25519_request(envelope, self.registry, self.replay, now=1000)

    def test_rotation_invalidates_old_version(self):
        old = sign_ed25519_request("agent-a", {"permission": "read"}, self.private,
                                   timestamp=1000, nonce="d" * 16)
        rotate_ed25519_agent("agent-a", self.private_dir, self.registry)
        with self.assertRaises(Ed25519IdentityError):
            verify_ed25519_request(old, self.registry, self.replay, now=1000)
        new = sign_ed25519_request("agent-a", {"permission": "read"},
                                   self.private_dir / "agent-a.ed25519.pem",
                                   key_version=2, timestamp=1000, nonce="e" * 16)
        self.assertTrue(verify_ed25519_request(new, self.registry, self.replay, now=1000)["authenticated"])

    def test_revocation_rejected(self):
        revoke_ed25519_agent("agent-a", self.registry)
        envelope = sign_ed25519_request("agent-a", {"permission": "read"}, self.private,
                                        timestamp=1000, nonce="f" * 16)
        with self.assertRaises(Ed25519IdentityError):
            verify_ed25519_request(envelope, self.registry, self.replay, now=1000)


if __name__ == "__main__":
    unittest.main()
