import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from papi_core.local_store import append_local_record, load_local_records
from papi_core.sqlite_backup import create_sqlite_backup
from papi_core.sqlite_backup_crypto import (
    BackupEncryptionError, decrypt_sqlite_backup, encrypt_sqlite_backup,
    generate_backup_key, rotate_encrypted_backup_key, verify_encrypted_backup,
)


class SQLiteBackupCryptoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "source.sqlite3"
        append_local_record(self.db, kind="memory", record_id="m-1",
                            event_id="e-1", created_at="2026-11-14T12:00:00Z",
                            record={"memory_id": "m-1", "content": "secret"})
        self.backup = create_sqlite_backup(self.db, self.root / "plain-backups")
        self.key = self.root / "keys" / "backup.key"
        generate_backup_key(self.key)
        self.manifest = self.root / "encrypted" / "backup.manifest.json"
        self.encrypted = encrypt_sqlite_backup(self.backup["backup_path"], self.key, self.manifest)

    def tearDown(self):
        self.temp.cleanup()

    def test_encrypted_backup_authenticates_and_checks_sqlite_without_user_plaintext(self):
        result = verify_encrypted_backup(self.manifest, self.key)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["algorithm"], "AES-256-GCM")
        self.assertFalse(result["plaintext_written_to_user_path"])
        self.assertFalse(Path(self.encrypted["encrypted_path"]).read_bytes().startswith(b"SQLite format 3"))

    def test_decrypt_restores_valid_sqlite_and_preserves_source_backup(self):
        destination = self.root / "decrypted" / "restored.sqlite3"
        result = decrypt_sqlite_backup(self.manifest, self.key, destination)
        self.assertEqual(result["status"], "decrypted")
        self.assertEqual(load_local_records(destination, "memory")[0]["content"], "secret")
        self.assertTrue(Path(self.backup["backup_path"]).exists())

    def test_wrong_key_is_rejected(self):
        wrong = self.root / "wrong.key"
        generate_backup_key(wrong)
        with self.assertRaises(BackupEncryptionError):
            verify_encrypted_backup(self.manifest, wrong)

    def test_ciphertext_tampering_is_rejected(self):
        encrypted_path = Path(self.encrypted["encrypted_path"])
        encrypted_path.write_bytes(encrypted_path.read_bytes()[:-1] + b"x")
        with self.assertRaises(BackupEncryptionError):
            verify_encrypted_backup(self.manifest, self.key)

    def test_key_generation_refuses_overwrite_and_permissions_are_restrictive(self):
        with self.assertRaises(BackupEncryptionError):
            generate_backup_key(self.key)
        if os.name == "posix":
            self.assertEqual(self.key.stat().st_mode & 0o077, 0)

    def test_key_rotation_reencrypts_and_keeps_old_artifacts(self):
        new_key = self.root / "keys" / "rotated.key"
        generate_backup_key(new_key)
        new_manifest = self.root / "rotated" / "backup.manifest.json"
        result = rotate_encrypted_backup_key(self.manifest, self.key, new_key, new_manifest)
        self.assertEqual(result["status"], "key_rotated")
        self.assertTrue(result["old_backup_preserved"])
        self.assertEqual(verify_encrypted_backup(new_manifest, new_key)["status"], "verified")
        with self.assertRaises(BackupEncryptionError):
            verify_encrypted_backup(new_manifest, self.key)

    def test_decrypt_refuses_existing_destination(self):
        destination = self.root / "existing.sqlite3"
        destination.write_bytes(b"do-not-overwrite")
        with self.assertRaises(BackupEncryptionError):
            decrypt_sqlite_backup(self.manifest, self.key, destination)
        self.assertEqual(destination.read_bytes(), b"do-not-overwrite")

    def test_manifest_authentication_prevents_algorithm_or_nonce_tampering(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["algorithm"] = "AES-128-GCM"
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(BackupEncryptionError):
            verify_encrypted_backup(self.manifest, self.key)


if __name__ == "__main__":
    unittest.main()
