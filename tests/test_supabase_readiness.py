import contextlib
import io
import sys
import unittest
from unittest.mock import patch

from papi_core import __main__ as cli
from papi_core.storage import SupabaseStore


class SupabaseReadinessTests(unittest.TestCase):
    def setUp(self):
        self.store = SupabaseStore(url="https://example.supabase.co", key="test-key")

    def test_reports_ready_when_both_tables_are_readable(self):
        with patch.object(self.store, "_request", side_effect=[[], []]) as request:
            result = self.store.check_readiness()
        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["network_test_performed"])
        self.assertFalse(result["writes_performed"])
        self.assertFalse(result["secrets_displayed"])
        self.assertEqual(request.call_count, 2)

    def test_reports_incomplete_when_one_table_is_unavailable(self):
        from papi_core.storage import StoreError
        with patch.object(self.store, "_request", side_effect=[[], StoreError("HTTP 403")]):
            result = self.store.check_readiness()
        self.assertEqual(result["status"], "incomplete")
        self.assertTrue(result["checks"]["papi_tasks"]["readable"])
        self.assertFalse(result["checks"]["papi_audit_events"]["readable"])
        self.assertNotIn("HTTP 403", str(result))

    def test_cli_returns_nonzero_for_incomplete_supabase(self):
        output = io.StringIO()
        with patch.object(sys, "argv", ["papi", "supabase-check"]), \
             patch.object(cli, "SupabaseStore") as store_class, \
             contextlib.redirect_stdout(output):
            store_class.return_value.check_readiness.return_value = {
                "status": "incomplete", "writes_performed": False
            }
            code = cli.main()
        self.assertEqual(code, 2)
        self.assertIn('"incomplete"', output.getvalue())


if __name__ == "__main__":
    unittest.main()
