import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from papi_core.papi_kids_backup import (
    PapiKidsBackupError,
    decrypt_and_verify_pg_dump_archive,
    encrypt_pg_dump_archive,
)


class PapiKidsBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "database.dump"
        self.source.write_bytes(b"PGDMP" + b"sample backup payload" * 1000)
        self.key = base64.b64encode(b"K" * 32).decode("ascii")
        self.env = {"PAPI_KIDS_BACKUP_KEY_B64": self.key}

    def tearDown(self):
        self.temp.cleanup()

    def test_encrypts_and_restores_with_authenticated_integrity(self):
        with patch.dict(os.environ, self.env, clear=True):
            result = encrypt_pg_dump_archive(
                self.source, self.root, key_id="backup-key-2026-01"
            )
            encrypted = Path(result["backup_path"])
            manifest = Path(result["manifest_path"])
            restored = self.root / "restored.dump"
            verified = decrypt_and_verify_pg_dump_archive(
                encrypted, manifest, restored
            )
        self.assertTrue(result["manifest"]["encrypted"])
        self.assertEqual(encrypted.stat().st_mode & 0o777, 0o600)
        self.assertEqual(restored.read_bytes(), self.source.read_bytes())
        self.assertTrue(verified["gcm_authentication_verified"])
        self.assertFalse(verified["database_restore_performed"])

    def test_wrong_key_fails_authentication(self):
        with patch.dict(os.environ, self.env, clear=True):
            result = encrypt_pg_dump_archive(
                self.source, self.root, key_id="backup-key-2026-01"
            )
        with patch.dict(os.environ, {"PAPI_KIDS_BACKUP_KEY_B64": base64.b64encode(b"X"*32).decode()}, clear=True):
            with self.assertRaises(PapiKidsBackupError):
                decrypt_and_verify_pg_dump_archive(
                    result["backup_path"], result["manifest_path"],
                    self.root / "wrong-key.dump",
                )

    def test_tampered_ciphertext_is_rejected_before_decryption(self):
        with patch.dict(os.environ, self.env, clear=True):
            result = encrypt_pg_dump_archive(
                self.source, self.root, key_id="backup-key-2026-01"
            )
        path = Path(result["backup_path"])
        data = bytearray(path.read_bytes())
        data[-20] ^= 0x01
        path.write_bytes(data)
        with patch.dict(os.environ, self.env, clear=True):
            with self.assertRaises(PapiKidsBackupError):
                decrypt_and_verify_pg_dump_archive(
                    path, result["manifest_path"], self.root / "tampered.dump"
                )

    def test_rejects_non_pg_dump_source_and_bad_key(self):
        invalid = self.root / "not-a-dump"
        invalid.write_bytes(b"not a database backup")
        with patch.dict(os.environ, self.env, clear=True):
            with self.assertRaises(PapiKidsBackupError):
                encrypt_pg_dump_archive(invalid, self.root, key_id="k1")
        with patch.dict(os.environ, {"PAPI_KIDS_BACKUP_KEY_B64": "short"}, clear=True):
            with self.assertRaises(PapiKidsBackupError):
                encrypt_pg_dump_archive(self.source, self.root, key_id="k1")


if __name__ == "__main__":
    unittest.main()
