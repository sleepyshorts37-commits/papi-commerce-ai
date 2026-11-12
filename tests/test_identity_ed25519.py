import os
import tempfile
import unittest
from pathlib import Path

from papi_core.identity_ed25519 import (
    Ed25519IdentityError, _registry_locked, provision_ed25519_agent, revoke_ed25519_agent,
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

    def test_concurrent_rotations_serialize_registry_versions(self):
        from concurrent.futures import ThreadPoolExecutor
        import json

        def rotate():
            return rotate_ed25519_agent("agent-a", self.private_dir, self.registry)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: rotate(), range(2)))

        self.assertEqual(results, [self.private, self.private])
        registry = json.loads(self.registry.read_text(encoding="utf-8"))
        self.assertEqual(registry["agents"]["agent-a"]["key_version"], 3)
        envelope = sign_ed25519_request(
            "agent-a", {"permission": "read"}, self.private,
            key_version=3, timestamp=1000, nonce="rotation-lock-test-0001")
        self.assertTrue(verify_ed25519_request(
            envelope, self.registry, self.replay, now=1000)["authenticated"])

    def test_revocation_rejected(self):
        revoke_ed25519_agent("agent-a", self.registry)
        envelope = sign_ed25519_request("agent-a", {"permission": "read"}, self.private,
                                        timestamp=1000, nonce="f" * 16)
        with self.assertRaises(Ed25519IdentityError):
            verify_ed25519_request(envelope, self.registry, self.replay, now=1000)


    def test_agent_id_tampering_rejected(self):
        envelope = sign_ed25519_request("agent-a", {"permission": "read"}, self.private,
                                        timestamp=1000, nonce="g" * 16)
        envelope["agent_id"] = "agent-b"
        with self.assertRaises(Ed25519IdentityError):
            verify_ed25519_request(envelope, self.registry, self.replay, now=1000)

    def test_expired_signature_rejected_before_replay_database(self):
        envelope = sign_ed25519_request("agent-a", {"permission": "read"}, self.private,
                                        timestamp=1000, nonce="h" * 16)
        with self.assertRaises(Ed25519IdentityError):
            verify_ed25519_request(envelope, self.registry, self.replay, now=1301)
        self.assertFalse(self.replay.exists())

    def test_wrong_key_version_rejected(self):
        envelope = sign_ed25519_request("agent-a", {"permission": "read"}, self.private,
                                        key_version=2, timestamp=1000, nonce="i" * 16)
        with self.assertRaises(Ed25519IdentityError):
            verify_ed25519_request(envelope, self.registry, self.replay, now=1000)

    def test_short_nonce_rejected_when_signing(self):
        with self.assertRaises(Ed25519IdentityError):
            sign_ed25519_request("agent-a", {"permission": "read"}, self.private,
                                 timestamp=1000, nonce="short")


    def test_one_agents_key_cannot_authenticate_another_agent(self):
        provision_ed25519_agent("agent-b", self.private_dir, self.registry)
        envelope = sign_ed25519_request("agent-a", {"permission": "read"}, self.private,
                                        timestamp=1000, nonce="j" * 16)
        envelope["agent_id"] = "agent-b"
        with self.assertRaises(Ed25519IdentityError):
            verify_ed25519_request(envelope, self.registry, self.replay, now=1000)

    def test_concurrent_replay_allows_exactly_one_verification(self):
        from concurrent.futures import ThreadPoolExecutor

        envelope = sign_ed25519_request("agent-a", {"permission": "read"}, self.private,
                                        timestamp=1000, nonce="k" * 24)

        def attempt():
            try:
                verify_ed25519_request(envelope, self.registry, self.replay, now=1000)
                return "accepted"
            except Ed25519IdentityError:
                return "rejected"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt(), range(2)))
        self.assertEqual(results.count("accepted"), 1)
        self.assertEqual(results.count("rejected"), 1)


    def test_registry_lock_uses_declared_default_path(self):
        def operation(registry_path=self.registry):
            return registry_path

        locked_operation = _registry_locked("registry_path")(operation)
        self.assertEqual(locked_operation(), self.registry)
        self.assertTrue(self.registry.with_name(self.registry.name + ".lock").is_file())


    def test_registry_lock_rejects_symlink_lock_file(self):
        registry_path = self.root / "symlink-registry.json"
        lock_path = registry_path.with_name(registry_path.name + ".lock")
        target = self.root / "lock-target"
        target.write_text("unchanged", encoding="utf-8")
        lock_path.symlink_to(target)

        def operation(registry_path=registry_path):
            return registry_path

        with self.assertRaises(OSError):
            _registry_locked("registry_path")(operation)()
        self.assertEqual(target.read_text(encoding="utf-8"), "unchanged")

    def test_registry_lock_rejects_group_or_world_access(self):
        lock_path = self.registry.with_name(self.registry.name + ".lock")
        lock_path.touch()
        lock_path.chmod(0o644)

        def operation(registry_path=self.registry):
            return registry_path

        with self.assertRaises(PermissionError):
            _registry_locked("registry_path")(operation)()

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO support required")
    def test_registry_lock_rejects_fifo_without_blocking(self):
        registry_path = self.root / "fifo-registry.json"
        lock_path = registry_path.with_name(registry_path.name + ".lock")
        os.mkfifo(lock_path, 0o600)

        def operation(registry_path=registry_path):
            return registry_path

        with self.assertRaises(PermissionError):
            _registry_locked("registry_path")(operation)()


if __name__ == "__main__":
    unittest.main()
