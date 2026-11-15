import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from papi_core.papi_kids_backup import encrypt_pg_dump_archive
from papi_core.papi_kids_restore_drill import (
    PapiKidsRestoreDrillError,
    run_isolated_restore_drill,
)


class PapiKidsRestoreDrillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "database.dump"
        self.source.write_bytes(b"PGDMP" + b"backup payload")
        self.key = base64.b64encode(b"R" * 32).decode()
        with patch.dict(os.environ, {"PAPI_KIDS_BACKUP_KEY_B64": self.key}, clear=True):
            self.backup = encrypt_pg_dump_archive(
                self.source, self.root, key_id="restore-test-key"
            )

    def tearDown(self):
        self.temp.cleanup()

    def env(self):
        return {
            "PAPI_KIDS_BACKUP_KEY_B64": self.key,
            "PAPI_KIDS_DATABASE_URL": "postgresql://prod:prodsecret@db.example.com/papi_prod?sslmode=require",
            "PAPI_KIDS_RESTORE_TEST_DATABASE_URL": "postgresql://test:testsecret@db.example.com/papi_restore_test?sslmode=require",
            "PATH": "/usr/bin",
        }

    def test_requires_explicit_authorization_and_isolated_database_name(self):
        with patch.dict(os.environ, self.env(), clear=True):
            with self.assertRaises(PapiKidsRestoreDrillError):
                run_isolated_restore_drill(
                    self.backup["backup_path"], self.backup["manifest_path"], self.root,
                    expected_database_name="papi_restore_test", restore_authorized=False,
                )
            with self.assertRaises(PapiKidsRestoreDrillError):
                run_isolated_restore_drill(
                    self.backup["backup_path"], self.backup["manifest_path"], self.root,
                    expected_database_name="papi_prod", restore_authorized=True,
                )

    def test_restores_only_to_explicit_test_database_without_secrets_in_argv(self):
        def fake_run(command, **kwargs):
            args = " ".join(command)
            self.assertNotIn("testsecret", args)
            self.assertNotIn("prodsecret", args)
            self.assertEqual(kwargs["env"]["PGDATABASE"], "papi_restore_test")
            archive = Path(command[-1])
            self.assertTrue(archive.read_bytes().startswith(b"PGDMP"))
            return type("Completed", (), {"returncode": 0})()
        with patch.dict(os.environ, self.env(), clear=True), patch(
            "papi_core.papi_kids_restore_drill.shutil.which", return_value="/usr/bin/pg_restore"
        ), patch(
            "papi_core.papi_kids_restore_drill.subprocess.run", side_effect=fake_run
        ):
            result = run_isolated_restore_drill(
                self.backup["backup_path"], self.backup["manifest_path"], self.root,
                expected_database_name="papi_restore_test", restore_authorized=True,
            )
        self.assertEqual(result["status"], "restore_drill_succeeded")
        self.assertFalse(result["production_database_modified"])
        self.assertFalse(any(self.root.glob(".papi-restore-drill-*")))

    def test_rejects_production_database_even_with_authorization(self):
        env = self.env()
        env["PAPI_KIDS_RESTORE_TEST_DATABASE_URL"] = env["PAPI_KIDS_DATABASE_URL"]
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(PapiKidsRestoreDrillError):
                run_isolated_restore_drill(
                    self.backup["backup_path"], self.backup["manifest_path"], self.root,
                    expected_database_name="papi_prod", restore_authorized=True,
                )


if __name__ == "__main__":
    unittest.main()
