import contextlib
import io
import sys
import unittest
from unittest.mock import patch

from papi_core import __main__ as cli


class RemoteDashboardCliTests(unittest.TestCase):
    def test_remote_dashboard_is_explicit_and_read_only(self):
        expected = {"mode": "read_only_remote", "controls": {"writes_performed": False}}
        output = io.StringIO()
        with patch.object(sys, "argv", ["papi", "dashboard-remote", "--page-size", "100", "--max-pages", "3"]), \
             patch.object(cli, "SupabaseStore") as store_class, \
             patch.object(cli, "build_remote_command_center", return_value=expected) as builder, \
             contextlib.redirect_stdout(output):
            code = cli.main()
        self.assertEqual(code, 0)
        store_class.assert_called_once_with()
        builder.assert_called_once_with(store_class.return_value, page_size=100, max_pages=3)
        self.assertIn('"read_only_remote"', output.getvalue())
        self.assertNotIn("test-key", output.getvalue())

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
