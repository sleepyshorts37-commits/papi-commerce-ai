import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from papi_core.papi_kids_backup_runner import (
    PapiKidsBackupRunnerError,
    run_backup_from_environment,
)


class PapiKidsBackupRunnerTests(unittest.TestCase):
    def test_runner_is_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(PapiKidsBackupRunnerError):
                run_backup_from_environment()

    def test_runner_requires_private_volume_and_key_id(self):
        with tempfile.TemporaryDirectory() as root:
            os.chmod(root, 0o700)
            env = {
                "PAPI_KIDS_BACKUP_ENABLED": "true",
                "PAPI_KIDS_BACKUP_DIRECTORY": root,
                "PAPI_KIDS_DATABASE_URL": "postgresql://backup:secret@db.example.com/papi?sslmode=require",
                "PAPI_KIDS_BACKUP_KEY_B64": base64.b64encode(b"K"*32).decode(),
                "PATH": "/usr/bin",
            }
            with patch.dict(os.environ, env, clear=True), patch(
                "papi_core.papi_kids_backup_runner.create_encrypted_postgres_backup",
                return_value={"backup_path": root + "/backup.enc", "manifest_path": root + "/backup.json"},
            ) as create:
                with self.assertRaises(PapiKidsBackupRunnerError):
                    run_backup_from_environment()
                create.assert_not_called()

    def test_runner_calls_encrypted_backup_only_when_explicitly_enabled(self):
        with tempfile.TemporaryDirectory() as root:
            os.chmod(root, 0o700)
            env = {
                "PAPI_KIDS_BACKUP_ENABLED": "true",
                "PAPI_KIDS_BACKUP_DIRECTORY": root,
                "PAPI_KIDS_BACKUP_KEY_ID": "backup-key-01",
                "PAPI_KIDS_DATABASE_URL": "postgresql://backup:secret@db.example.com/papi?sslmode=require",
                "PAPI_KIDS_BACKUP_KEY_B64": base64.b64encode(b"K"*32).decode(),
                "PATH": "/usr/bin",
            }
            with patch.dict(os.environ, env, clear=True), patch(
                "papi_core.papi_kids_backup_runner.create_encrypted_postgres_backup",
                return_value={"backup_path": root + "/backup.enc", "manifest_path": root + "/backup.json"},
            ) as create:
                result = run_backup_from_environment()
            create.assert_called_once()
            self.assertEqual(result["backup_path"], root + "/backup.enc")


if __name__ == "__main__":
    unittest.main()
