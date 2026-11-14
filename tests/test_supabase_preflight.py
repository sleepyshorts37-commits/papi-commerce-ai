import tempfile
import unittest
from pathlib import Path

from papi_core.supabase_preflight import (
    SupabasePreflightError,
    require_supabase_configuration,
    run_supabase_preflight,
)


class SupabasePreflightTests(unittest.TestCase):
    def _repo(self, root: Path, names=("004_initial.sql", "005_next.sql")):
        migrations = root / "infra" / "supabase" / "migrations"
        migrations.mkdir(parents=True)
        (root / "infra" / "supabase" / "schema.sql").write_text(
            "create table public.papi_tasks(id text primary key);\n", encoding="utf-8"
        )
        for name in names:
            (migrations / name).write_text("-- migration " + name + "\n", encoding="utf-8")

    def test_inventory_is_deterministic_and_reports_rollback_presence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            migrations = root / "infra" / "supabase" / "migrations"
            (migrations / "004_initial_down.sql").write_text("-- rollback\n", encoding="utf-8")
            report = run_supabase_preflight(root, {})
            self.assertEqual(report["status"], "blocked_missing_or_invalid_configuration")
            self.assertEqual(report["migration_count"], 2)
            self.assertEqual(report["first_migration"], "004")
            self.assertEqual(report["latest_migration"], "005")
            self.assertTrue(report["migrations"][0]["rollback_available"])
            self.assertFalse(report["migrations"][1]["rollback_available"])
            self.assertEqual(report["migrations"], run_supabase_preflight(root, {})["migrations"])

    def test_valid_configuration_is_reported_without_exposing_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            secret = "do-not-print-this-service-role-key"
            report = run_supabase_preflight(root, {
                "SUPABASE_URL": "https://project-ref.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": secret,
            })
            self.assertEqual(report["status"], "ready_for_operator_review")
            self.assertTrue(report["supabase_url_valid"])
            self.assertEqual(report["server_key_variable"], "SUPABASE_SERVICE_ROLE_KEY")
            self.assertNotIn(secret, repr(report))
            self.assertFalse(report["network_access_performed"])
            self.assertFalse(report["remote_changes_permitted"])
            require_supabase_configuration(report)

    def test_invalid_url_and_legacy_key_are_handled_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            report = run_supabase_preflight(root, {
                "SUPABASE_URL": "http://project-ref.supabase.co",
                "SUPABASE_KEY": "legacy-secret",
            })
            self.assertFalse(report["supabase_url_valid"])
            self.assertTrue(report["server_key_configured"])
            self.assertEqual(report["server_key_variable"], "SUPABASE_KEY")
            with self.assertRaises(SupabasePreflightError):
                require_supabase_configuration(report)

    def test_missing_migration_version_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root, ("004_initial.sql", "006_late.sql"))
            with self.assertRaisesRegex(SupabasePreflightError, "discontinue"):
                run_supabase_preflight(root, {})

    def test_duplicate_version_and_invalid_filename_are_blocked(self):
        for names, message in [
            (("004_initial.sql", "004_second.sql"), "dupliquée"),
            (("004_bad-name.sql",), "non conforme"),
        ]:
            with self.subTest(names=names), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self._repo(root, names)
                with self.assertRaisesRegex(SupabasePreflightError, message):
                    run_supabase_preflight(root, {})

    def test_tracked_or_local_env_file_blocks_operator_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            (root / ".env.production").write_text("SECRET=value", encoding="utf-8")
            report = run_supabase_preflight(root, {
                "SUPABASE_URL": "https://project-ref.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": "secret",
            })
            self.assertEqual(report["status"], "blocked_unsafe_env_files")
            self.assertEqual(report["environment_files_found"], [".env.production"])

    def test_env_example_is_allowed_but_not_real_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._repo(root)
            (root / ".env.example").write_text("SUPABASE_URL=\n", encoding="utf-8")
            report = run_supabase_preflight(root, {})
            self.assertEqual(report["environment_files_found"], [])


if __name__ == "__main__":
    unittest.main()
