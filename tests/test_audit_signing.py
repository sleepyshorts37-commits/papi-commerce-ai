"""Tests for the backend-only audit signing-provider boundary."""
import tempfile
import unittest
from pathlib import Path

from papi_core.audit_anchor_keys import LocalAuditKeyring
from papi_core.audit_signing import (
    AuditSigningProvider,
    LocalKeyringSigningProvider,
    SigningProviderError,
)


class AuditSigningProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.keyring = LocalAuditKeyring(Path(self.temp.name) / "keyring")
        self.provider = LocalKeyringSigningProvider(self.keyring)

    def tearDown(self):
        self.temp.cleanup()

    def test_local_provider_implements_contract_without_exporting_private_key(self):
        self.assertIsInstance(self.provider, AuditSigningProvider)
        key_id = self.keyring.provision()
        message = b"provider boundary payload"
        signature = self.provider.sign(key_id, message)
        self.assertTrue(self.provider.verify(key_id, message, signature))
        self.assertFalse(self.provider.verify(key_id, message + b"x", signature))
        self.assertFalse(hasattr(self.provider, "private_key"))
        self.assertFalse(hasattr(self.provider, "export_private_key"))

    def test_retired_key_remains_verifiable_after_rotation(self):
        old_id = self.keyring.provision()
        message = b"historical signed record"
        signature = self.provider.sign(old_id, message)
        self.keyring.rotate(old_id)
        self.assertTrue(self.provider.verify(old_id, message, signature))

    def test_revoked_key_fails_closed(self):
        key_id = self.keyring.provision()
        message = b"revoked record"
        signature = self.provider.sign(key_id, message)
        self.keyring.revoke(key_id)
        self.assertFalse(self.provider.verify(key_id, message, signature))
        with self.assertRaises(SigningProviderError):
            self.provider.sign(key_id, message)

    def test_invalid_keyring_is_rejected_at_construction(self):
        with self.assertRaises(SigningProviderError):
            LocalKeyringSigningProvider(object())

    def test_provider_errors_are_normalized_and_fail_closed(self):
        class BrokenKeyring(LocalAuditKeyring):
            def sign(self, key_id, message):
                raise OSError("backend unavailable")

            def verify(self, key_id, message, signature_hex):
                raise OSError("backend unavailable")

        broken = LocalKeyringSigningProvider(BrokenKeyring(Path(self.temp.name) / "broken"))
        with self.assertRaises(SigningProviderError):
            broken.sign("audit-" + "0" * 32, b"x")
        with self.assertRaises(SigningProviderError):
            broken.verify("audit-" + "0" * 32, b"x", "00" * 64)


if __name__ == "__main__":
    unittest.main()
