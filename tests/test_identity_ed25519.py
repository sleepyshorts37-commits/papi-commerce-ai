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

    def test_rotation_preserves_old_public_key_for_historical_audit_only(self):
        old = sign_ed25519_request("agent-a", {"permission": "read"}, self.private,
                                   timestamp=1000, nonce="l" * 16)
        rotate_ed25519_agent("agent-a", self.private_dir, self.registry)
        from papi_core.identity_ed25519 import verify_ed25519_archived_signature
        result = verify_ed25519_archived_signature(old, self.registry)
        self.assertTrue(result["signature_verified"])
        self.assertTrue(result["historical_key"])
        self.assertFalse(result["authorization_granted"])
        self.assertFalse(result["nonce_consumed"])
        with self.assertRaises(Ed25519IdentityError):
            verify_ed25519_request(old, self.registry, self.replay, now=1000)

    def test_revoked_key_remains_verifiable_for_historical_audit_only(self):
        old = sign_ed25519_request("agent-a", {"permission": "read"}, self.private,
                                   timestamp=1000, nonce="m" * 16)
        revoke_ed25519_agent("agent-a", self.registry)
        from papi_core.identity_ed25519 import verify_ed25519_archived_signature
        result = verify_ed25519_archived_signature(old, self.registry)
        self.assertTrue(result["signature_verified"])
        self.assertFalse(result["authorization_granted"])
        with self.assertRaises(Ed25519IdentityError):
            verify_ed25519_request(old, self.registry, self.replay, now=1000)

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

    def test_expired_signature_cannot_bypass_freshness_and_consume_nonce(self):
        envelope = sign_ed25519_request("agent-a", {"permission": "read"}, self.private,
                                        timestamp=1000, nonce="z" * 16)
        with self.assertRaises(Ed25519IdentityError):
            verify_ed25519_request(envelope, self.registry, self.replay,
                                   now=1301, allow_expired=True, consume_nonce=True)
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


    def test_rotation_rejects_invalid_history_before_replacing_private_key(self):
        import json

        registry = json.loads(self.registry.read_text(encoding="utf-8"))
        registry["agents"]["agent-a"]["key_history"] = "invalid"
        self.registry.write_text(json.dumps(registry), encoding="utf-8")
        old_private = self.private.read_bytes()

        with self.assertRaises(Ed25519IdentityError):
            rotate_ed25519_agent("agent-a", self.private_dir, self.registry)

        self.assertEqual(self.private.read_bytes(), old_private)

    def test_current_verifiers_reject_boolean_registry_key_version(self):
        import json
        from papi_core.identity_ed25519 import verify_ed25519_archived_signature

        envelope = sign_ed25519_request(
            "agent-a", {"permission": "read"}, self.private,
            timestamp=1000, nonce="boolean-current-version-0001",
        )
        registry = json.loads(self.registry.read_text(encoding="utf-8"))
        registry["agents"]["agent-a"]["key_version"] = True
        self.registry.write_text(json.dumps(registry), encoding="utf-8")

        with self.assertRaises(Ed25519IdentityError):
            verify_ed25519_archived_signature(envelope, self.registry)
        with self.assertRaises(Ed25519IdentityError):
            verify_ed25519_request(envelope, self.registry, self.replay, now=1000)

    def test_archived_verifier_rejects_boolean_historical_key_version(self):
        import json
        from papi_core.identity_ed25519 import verify_ed25519_archived_signature

        old = sign_ed25519_request(
            "agent-a", {"permission": "read"}, self.private,
            timestamp=1000, nonce="boolean-history-version-0001",
        )
        rotate_ed25519_agent("agent-a", self.private_dir, self.registry)
        registry = json.loads(self.registry.read_text(encoding="utf-8"))
        registry["agents"]["agent-a"]["key_history"][0]["key_version"] = True
        self.registry.write_text(json.dumps(registry), encoding="utf-8")

        with self.assertRaises(Ed25519IdentityError):
            verify_ed25519_archived_signature(old, self.registry)



    def test_rotation_journal_recovers_crash_after_private_key_replace(self):
        import json
        from unittest.mock import patch
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from papi_core import rotation_journal

        old_private = self.private.read_bytes()
        old_registry = self.registry.read_bytes()
        key = Ed25519PrivateKey.generate()
        new_private = key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        registry = json.loads(old_registry)
        registry["agents"]["agent-a"]["key_version"] = 2
        registry["agents"]["agent-a"]["public_key"] = key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
        registry["agents"]["agent-a"]["key_history"] = [{
            "key_version": 1,
            "public_key": json.loads(old_registry)["agents"]["agent-a"]["public_key"],
            "retired_at": 123,
        }]
        new_registry = (json.dumps(registry, sort_keys=True, indent=2) + "\\n").encode()

        real_write = rotation_journal._atomic_write
        calls = 0
        def crash_before_registry(path, content):
            nonlocal calls
            calls += 1
            if calls == 1:
                return real_write(path, content)
            if calls == 2:
                return real_write(path, content)
            raise SystemExit("simulated process crash")

        with patch.object(rotation_journal, "_atomic_write", side_effect=crash_before_registry):
            with self.assertRaises(SystemExit):
                rotation_journal.commit_key_rotation(
                    self.private, self.registry, old_private, new_private,
                    old_registry, new_registry,
                )

        self.assertNotEqual(self.private.read_bytes(), old_private)
        self.assertEqual(self.registry.read_bytes(), old_registry)
        self.assertTrue(self.private.with_name(self.private.name + ".rotation-journal").exists())
        self.assertEqual(rotation_journal.recover_key_rotation(self.private, self.registry), "rolled_back")
        self.assertEqual(self.private.read_bytes(), old_private)
        self.assertEqual(self.registry.read_bytes(), old_registry)
        self.assertFalse(self.private.with_name(self.private.name + ".rotation-journal").exists())

    def test_rotation_journal_recovers_committed_pair_after_cleanup_crash(self):
        import json
        from unittest.mock import patch
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from papi_core import rotation_journal

        old_private = self.private.read_bytes()
        old_registry = self.registry.read_bytes()
        key = Ed25519PrivateKey.generate()
        new_private = key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        registry = json.loads(old_registry)
        registry["agents"]["agent-a"]["key_version"] = 2
        registry["agents"]["agent-a"]["public_key"] = key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
        registry["agents"]["agent-a"]["key_history"] = [{
            "key_version": 1,
            "public_key": json.loads(old_registry)["agents"]["agent-a"]["public_key"],
            "retired_at": 123,
        }]
        new_registry = (json.dumps(registry, sort_keys=True, indent=2) + "\\n").encode()

        with patch.object(rotation_journal, "_remove_journal", side_effect=SystemExit("crash after commit")):
            with self.assertRaises(SystemExit):
                rotation_journal.commit_key_rotation(
                    self.private, self.registry, old_private, new_private,
                    old_registry, new_registry,
                )

        self.assertEqual(self.registry.read_bytes(), new_registry)
        self.assertEqual(rotation_journal.recover_key_rotation(self.private, self.registry), "committed")
        self.assertEqual(self.private.read_bytes(), new_private)
        self.assertFalse(self.private.with_name(self.private.name + ".rotation-journal").exists())

    def test_rotation_journal_fails_closed_and_preserves_evidence_on_ambiguous_state(self):
        import json
        from unittest.mock import patch
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from papi_core import rotation_journal

        old_private = self.private.read_bytes()
        old_registry = self.registry.read_bytes()
        key = Ed25519PrivateKey.generate()
        new_private = key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        registry = json.loads(old_registry)
        registry["agents"]["agent-a"]["key_version"] = 2
        registry["agents"]["agent-a"]["public_key"] = key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
        registry["agents"]["agent-a"]["key_history"] = [{
            "key_version": 1,
            "public_key": json.loads(old_registry)["agents"]["agent-a"]["public_key"],
            "retired_at": 123,
        }]
        new_registry = (json.dumps(registry, sort_keys=True, indent=2) + "\\n").encode()

        real_write = rotation_journal._atomic_write
        calls = 0
        def crash_before_registry(path, content):
            nonlocal calls
            calls += 1
            if calls <= 2:
                return real_write(path, content)
            raise SystemExit("simulated process crash")

        with patch.object(rotation_journal, "_atomic_write", side_effect=crash_before_registry):
            with self.assertRaises(SystemExit):
                rotation_journal.commit_key_rotation(
                    self.private, self.registry, old_private, new_private,
                    old_registry, new_registry,
                )

        self.registry.write_bytes(b"tampered registry")
        journal = self.private.with_name(self.private.name + ".rotation-journal")
        with self.assertRaises(rotation_journal.RotationJournalError):
            rotation_journal.recover_key_rotation(self.private, self.registry)
        self.assertTrue(journal.exists())


    def test_signer_recovers_pending_rotation_before_using_private_key(self):
        from unittest.mock import patch
        from papi_core import rotation_journal

        old_private = self.private.read_bytes()
        old_registry = self.registry.read_bytes()
        new_private = b"new private key fixture"
        new_registry = b'{"schema_version":1,"agents":{}}'
        real_write = rotation_journal._atomic_write
        calls = 0
        def crash_before_registry(path, content):
            nonlocal calls
            calls += 1
            if calls <= 2:
                return real_write(path, content)
            raise SystemExit("simulated process crash")

        with patch.object(rotation_journal, "_atomic_write", side_effect=crash_before_registry):
            with self.assertRaises(SystemExit):
                rotation_journal.commit_key_rotation(
                    self.private, self.registry, old_private, new_private,
                    old_registry, new_registry,
                )

        envelope = sign_ed25519_request(
            "agent-a", {"permission": "read"}, self.private,
            timestamp=1000, nonce="recovery-before-signing-0001",
            registry_path=self.registry,
        )
        self.assertTrue(verify_ed25519_request(
            envelope, self.registry, self.replay, now=1000)["authenticated"])
        self.assertFalse(self.private.with_name(self.private.name + ".rotation-journal").exists())


if __name__ == "__main__":
    unittest.main()
