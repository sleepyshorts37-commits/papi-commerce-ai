import contextlib
import io
import sys
import unittest
from unittest.mock import patch

from papi_core import __main__ as cli


class RemoteDashboardCliTests(unittest.TestCase):
    def test_remote_dashboard_runs_preflight_before_loading_data(self):
        expected = {"mode": "read_only_remote", "controls": {"writes_performed": False}}
        preflight = {"status": "ready", "writes_performed": False, "secrets_displayed": False}
        output = io.StringIO()
        with patch.object(sys, "argv", ["papi", "dashboard-remote", "--page-size", "100", "--max-pages", "3"]), \
             patch.object(cli, "SupabaseStore") as store_class, \
             patch.object(cli, "build_remote_command_center", return_value=expected) as builder, \
             contextlib.redirect_stdout(output):
            store_class.return_value.check_readiness.return_value = preflight
            code = cli.main()
        self.assertEqual(code, 0)
        store_class.assert_called_once_with()
        store_class.return_value.check_readiness.assert_called_once_with()
        builder.assert_called_once_with(store_class.return_value, page_size=100, max_pages=3)
        self.assertIn('"read_only_remote"', output.getvalue())
        self.assertIn('"preflight"', output.getvalue())
        self.assertNotIn("test-key", output.getvalue())

    def test_incomplete_preflight_blocks_full_remote_reads(self):
        preflight = {
            "status": "incomplete",
            "checks": {"papi_tasks": {"readable": True}, "papi_audit_events": {"readable": False}},
            "writes_performed": False,
        }
        output = io.StringIO()
        with patch.object(sys, "argv", ["papi", "dashboard-remote"]), \
             patch.object(cli, "SupabaseStore") as store_class, \
             patch.object(cli, "build_remote_command_center") as builder, \
             contextlib.redirect_stdout(output):
            store_class.return_value.check_readiness.return_value = preflight
            code = cli.main()
        self.assertEqual(code, 2)
        builder.assert_not_called()
        self.assertIn('"blocked"', output.getvalue())
        self.assertIn('"remote_data_loaded": false', output.getvalue())

    def test_remote_dashboard_reports_missing_configuration(self):
        output = io.StringIO()
        errors = io.StringIO()
        with patch.object(sys, "argv", ["papi", "dashboard-remote"]), \
             patch.object(cli, "SupabaseStore", side_effect=cli.StoreError("Configurer SUPABASE_URL et SUPABASE_KEY.")), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = cli.main()
        self.assertEqual(code, 2)
        self.assertIn("Configurer SUPABASE_URL", errors.getvalue())
        self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
