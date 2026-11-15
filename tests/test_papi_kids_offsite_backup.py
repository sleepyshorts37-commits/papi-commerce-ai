import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from papi_core.papi_kids_offsite_backup import (
    PapiKidsOffsiteBackupError,
    copy_encrypted_backups_offsite,
)


class PapiKidsOffsiteBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.backup = self.root / "backup-01.pgdump.aesgcm"
        self.backup.write_bytes(b"encrypted payload")
        self.manifest = Path(str(self.backup) + ".json")
        self.manifest.write_text(json.dumps({
            "backup_file": self.backup.name, "encrypted": True,
            "encrypted_sha256": hashlib.sha256(self.backup.read_bytes()).hexdigest(),
        }))
        self.config = self.root / "rclone.conf"
        self.config.write_text("[remote]\ntype = drive\ntoken = secret-token\n")
        os.chmod(self.config, 0o600)

    def tearDown(self):
        self.temp.cleanup()

    def test_copies_and_checks_only_encrypted_backup_pairs(self):
        def fake_run(command, **kwargs):
            args = " ".join(command)
            self.assertNotIn("secret-token", args)
            self.assertEqual(kwargs["env"]["RCLONE_CONFIG"], str(self.config))
            return type("Completed", (), {"returncode": 0})()
        with patch.dict(os.environ, {"RCLONE_CONFIG": str(self.config), "PATH": "/usr/bin"}, clear=True), patch(
            "papi_core.papi_kids_offsite_backup.shutil.which", return_value="/usr/bin/rclone"
        ), patch(
            "papi_core.papi_kids_offsite_backup.subprocess.run", side_effect=fake_run
        ) as run:
            result = copy_encrypted_backups_offsite(
                self.root, remote="drive:papi-kids-backups",
                enabled=True,
            )
        self.assertEqual(result["files_copied_and_checked"], 2)
        self.assertFalse(result["remote_deletions_performed"])
        self.assertEqual(run.call_count, 2)
        self.assertIn("copy", run.call_args_list[0].args[0])
        self.assertIn("check", run.call_args_list[1].args[0])
        proof = json.loads((self.root / "offsite-verification.json").read_text())
        self.assertEqual(proof["status"], "offsite_copy_verified")
        self.assertTrue(proof["backups"][0]["offsite_copy_verified"])
        self.assertEqual((self.root / "offsite-verification.json").stat().st_mode & 0o777, 0o600)

    def test_disabled_remote_invalid_or_bad_config_fails_closed(self):
        with patch.dict(os.environ, {"RCLONE_CONFIG": str(self.config)}, clear=True):
            with self.assertRaises(PapiKidsOffsiteBackupError):
                copy_encrypted_backups_offsite(self.root, remote="drive:folder", enabled=False)
            with self.assertRaises(PapiKidsOffsiteBackupError):
                copy_encrypted_backups_offsite(self.root, remote="drive:../unsafe", enabled=True)
        os.chmod(self.config, 0o644)
        with patch.dict(os.environ, {"RCLONE_CONFIG": str(self.config)}, clear=True):
            with self.assertRaises(PapiKidsOffsiteBackupError):
                copy_encrypted_backups_offsite(self.root, remote="drive:folder", enabled=True)

    def test_tampered_backup_manifest_is_rejected_before_rclone(self):
        self.backup.write_bytes(b"tampered")
        with patch.dict(os.environ, {"RCLONE_CONFIG": str(self.config)}, clear=True), patch(
            "papi_core.papi_kids_offsite_backup.shutil.which", return_value="/usr/bin/rclone"
        ), patch("papi_core.papi_kids_offsite_backup.subprocess.run") as run:
            with self.assertRaises(PapiKidsOffsiteBackupError):
                copy_encrypted_backups_offsite(self.root, remote="drive:folder", enabled=True)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
