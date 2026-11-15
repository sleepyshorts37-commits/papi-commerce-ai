import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from papi_core.papi_kids_backup_job import (
    PapiKidsBackupJobError,
    _database_environment,
    create_encrypted_postgres_backup,
)


class PapiKidsBackupJobTests(unittest.TestCase):
    def test_database_url_requires_tls_and_password(self):
        with self.assertRaises(PapiKidsBackupJobError):
            _database_environment("postgresql://user:pass@db.example.com/books")
        with self.assertRaises(PapiKidsBackupJobError):
            _database_environment("postgresql://user@db.example.com/books?sslmode=require")
        env = _database_environment(
            "postgresql://reader:p%40ss%3Aword@db.example.com:5433/books?sslmode=verify-full"
        )
        self.assertEqual(env["PGPASSWORD"], "p@ss:word")
        self.assertEqual(env["PGSSLMODE"], "verify-full")
        self.assertEqual(env["PGPORT"], "5433")

    def test_pg_dump_arguments_do_not_contain_credentials_and_plaintext_is_removed(self):
        with tempfile.TemporaryDirectory() as root:
            key = base64.b64encode(b"Z" * 32).decode()
            database_url = "postgresql://backup:topsecret@db.example.com:5432/papi?sslmode=require"
            def fake_run(command, **kwargs):
                self.assertNotIn("topsecret", " ".join(command))
                self.assertNotIn(database_url, " ".join(command))
                self.assertEqual(kwargs["env"]["PGPASSWORD"], "topsecret")
                self.assertEqual(kwargs["env"]["PGSSLMODE"], "require")
                output = Path(command[command.index("--file") + 1])
                output.write_bytes(b"PGDMP" + b"backup contents")
                return type("Completed", (), {"returncode": 0})()
            with patch.dict(os.environ, {
                "PAPI_KIDS_DATABASE_URL": database_url,
                "PAPI_KIDS_BACKUP_KEY_B64": key,
                "PATH": "/usr/bin",
            }, clear=True), patch(
                "papi_core.papi_kids_backup_job.shutil.which", return_value="/usr/bin/pg_dump"
            ), patch(
                "papi_core.papi_kids_backup_job.subprocess.run", side_effect=fake_run
            ):
                result = create_encrypted_postgres_backup(root, key_id="test-key")
            self.assertTrue(result["database_dump_created"])
            self.assertTrue(result["plaintext_staging_deleted"])
            self.assertFalse(any(Path(root).glob(".papi-pg-dump-*")))
            self.assertTrue(Path(result["backup_path"]).is_file())

    def test_pg_dump_failure_does_not_leak_stderr(self):
        with tempfile.TemporaryDirectory() as root:
            with patch.dict(os.environ, {
                "PAPI_KIDS_DATABASE_URL": "postgresql://backup:secret@db.example.com/papi?sslmode=require",
                "PAPI_KIDS_BACKUP_KEY_B64": base64.b64encode(b"Z"*32).decode(),
                "PATH": "/usr/bin",
            }, clear=True), patch(
                "papi_kids_backup_job.shutil.which", return_value="/usr/bin/pg_dump"
            ), patch(
                "papi_kids_backup_job.subprocess.run",
                return_value=type("Completed", (), {"returncode": 1, "stderr": b"secret token"})(),
            ):
                with self.assertRaisesRegex(PapiKidsBackupJobError, "détails sensibles masqués"):
                    create_encrypted_postgres_backup(root, key_id="test-key")

    def test_requires_mounted_backup_directory_and_binary(self):
        with tempfile.TemporaryDirectory() as root:
            with patch.dict(os.environ, {
                "PAPI_KIDS_DATABASE_URL": "postgresql://backup:secret@db.example.com/papi?sslmode=require",
            }, clear=True), patch(
                "papi_kids_backup_job.shutil.which", return_value=None
            ):
                with self.assertRaises(PapiKidsBackupJobError):
                    create_encrypted_postgres_backup(root, key_id="test-key")


if __name__ == "__main__":
    unittest.main()
