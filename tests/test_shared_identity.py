import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from papi_core.identity_ed25519 import provision_ed25519_agent, sign_ed25519_request
from papi_core.shared_identity import SupabaseIdentityVerifier


class FakeStore:
    def __init__(self, public_key_hex, consume=True):
        self.public_key_hex = public_key_hex
        self.consume = consume
        self.calls = []

    def _request(self, method, path, payload=None, prefer=None):
        self.calls.append((method, path, payload))
        if method == "GET":
            return [{"public_key_hex": self.public_key_hex}]
        return self.consume


class SharedIdentityTests(unittest.TestCase):
    def test_verifies_public_key_and_consumes_nonce_remotely(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "keys.json"
            private = provision_ed25519_agent("agent-a", root / "private", registry)
            from cryptography.hazmat.primitives.serialization import load_pem_private_key
            key = load_pem_private_key(private.read_bytes(), password=None)
            public_hex = key.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            ).hex()
            envelope = sign_ed25519_request("agent-a", {
                "permission": "read_reports", "task_id": "task-1", "handler": "report.preview"
            }, private, nonce="x" * 24)
            store = FakeStore(public_hex)
            result = SupabaseIdentityVerifier(store).verify(envelope)
            self.assertTrue(result["authenticated"])
            self.assertEqual(result["registry"], "supabase")
            self.assertEqual(len(store.calls), 2)
            self.assertEqual(store.calls[1][1], "rpc/papi_consume_agent_nonce")

    def test_replay_or_rpc_failure_is_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private = provision_ed25519_agent("agent-a", root / "private", root / "keys.json")
            from cryptography.hazmat.primitives.serialization import load_pem_private_key
            key = load_pem_private_key(private.read_bytes(), password=None)
            public_hex = key.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            ).hex()
            envelope = sign_ed25519_request("agent-a", {
                "permission": "read_reports", "task_id": "task-1", "handler": "report.preview"
            }, private, nonce="y" * 24)
            with self.assertRaises(ValueError):
                SupabaseIdentityVerifier(FakeStore(public_hex, consume=False)).verify(envelope)


if __name__ == "__main__":
    unittest.main()
