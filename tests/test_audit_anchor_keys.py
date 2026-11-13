"""Tests for the local Ed25519 audit signing-key lifecycle."""
import json
import os
import tempfile
import unittest
from pathlib import Path

from papi_core.audit_anchor_keys import AuditKeyError, LocalAuditKeyring


class AuditAnchorKeyringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "keyring"
        self.keyring = LocalAuditKeyring(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_provision_sign_and_verify(self):
        key_id = self.keyring.provision()
        message = b"canonical audit checkpoint payload"
        signature = self.keyring.sign(key_id, message)
        self.assertEqual(len(signature), 128)
        self.assertTrue(self.keyring.verify(key_id, message, signature))
        self.assertFalse(self.keyring.verify(key_id, message + b"x", signature))

    def test_rotation_retains_historical_public_key_for_verification(self):
        old_id = self.keyring.provision()
        message = b"historical checkpoint"
        old_signature = self.keyring.sign(old_id, message)
        new_id = self.keyring.rotate(old_id)
        self.assertNotEqual(old_id, new_id)
        self.assertTrue(self.keyring.verify(old_id, message, old_signature))
        self.assertFalse(self.keyring.verify(old_id, message, self.keyring.sign(new_id, message)))
        self.assertTrue(self.keyring.verify(new_id, message, self.keyring.sign(new_id, message)))
        with self.assertRaises(AuditKeyError):
            self.keyring.sign(old_id, message)

    def test_revocation_blocks_historical_verification_and_signing(self):
        key_id = self.keyring.provision()
        message = b"record signed before revocation"
        signature = self.keyring.sign(key_id, message)
        self.keyring.revoke(key_id)
        self.assertFalse(self.keyring.verify(key_id, message, signature))
        with self.assertRaises(AuditKeyError):
            self.keyring.sign(key_id, message)

    def test_unknown_and_malformed_key_ids_fail_closed(self):
        self.keyring.provision()
        self.assertFalse(self.keyring.verify("unknown", b"x", "00" * 64))
        self.assertFalse(self.keyring.verify("../private", b"x", "00" * 64))

    def test_corrupt_registry_fails_closed(self):
        self.keyring.provision()
        self.keyring.registry_path.write_text('{"schema_version":1,"keys":null}', encoding="utf-8")
        with self.assertRaises(AuditKeyError):
            self.keyring.sign("audit-" + "0" * 32, b"x")
        with self.assertRaises(AuditKeyError):
            self.keyring.rotate("audit-" + "0" * 32)

    def test_private_key_permissions_are_restrictive(self):
        key_id = self.keyring.provision()
        private_path = self.root / "private" / (key_id + ".pem")
        self.assertEqual(private_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.root / "private").stat().st_mode & 0o777, 0o700)
        os.chmod(private_path, 0o644)
        with self.assertRaises(AuditKeyError):
            self.keyring.sign(key_id, b"x")

    def test_private_public_key_mismatch_is_detected(self):
        key_id = self.keyring.provision()
        private_path = self.root / "private" / (key_id + ".pem")
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        other = Ed25519PrivateKey.generate()
        private_path.write_bytes(other.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()
        ))
        os.chmod(private_path, 0o600)
        with self.assertRaises(AuditKeyError):
            self.keyring.sign(key_id, b"x")

    def test_only_one_active_key_is_permitted(self):
        key_id = self.keyring.provision()
        data = json.loads(self.keyring.registry_path.read_text(encoding="utf-8"))
        data["keys"]["audit-" + "1" * 32] = dict(data["keys"][key_id])
        self.keyring.registry_path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(AuditKeyError):
            self.keyring.sign(key_id, b"x")

    def test_rotation_requires_current_active_key(self):
        key_id = self.keyring.provision()
        self.keyring.rotate(key_id)
        with self.assertRaises(AuditKeyError):
            self.keyring.rotate(key_id)


if __name__ == "__main__":
    unittest.main()
