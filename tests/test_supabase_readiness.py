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
        rpc_result = {
            "tasks": [], "audit_events": [],
            "tasks_truncated": False, "audit_events_truncated": False,
            "snapshot_consistency": "single_statement_snapshot",
        }
        with patch.object(self.store, "_request", side_effect=[[], [], rpc_result]) as request:
            result = self.store.check_readiness()
        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["network_test_performed"])
        self.assertTrue(result["checks"]["papi_get_dashboard_snapshot"]["callable"])
        self.assertFalse(result["writes_performed"])
        self.assertFalse(result["secrets_displayed"])
        self.assertEqual(request.call_count, 3)
        self.assertEqual(request.call_args_list[2].args[0], "POST")
        self.assertEqual(request.call_args_list[2].args[1], "rpc/papi_get_dashboard_snapshot")

    def test_reports_incomplete_when_one_table_is_unavailable(self):
        from papi_core.storage import StoreError
        with patch.object(self.store, "_request", side_effect=[[], StoreError("HTTP 403"), StoreError("HTTP 404")]):
            result = self.store.check_readiness()
        self.assertEqual(result["status"], "incomplete")
        self.assertTrue(result["checks"]["papi_tasks"]["readable"])
        self.assertFalse(result["checks"]["papi_audit_events"]["readable"])
        self.assertFalse(result["checks"]["papi_get_dashboard_snapshot"]["callable"])
        self.assertNotIn("HTTP 403", str(result))
        self.assertNotIn("HTTP 404", str(result))

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



    def test_reports_incomplete_when_snapshot_rpc_returns_wrong_shape(self):
        with patch.object(self.store, "_request", side_effect=[[], [], {"unexpected": True}]):
            result = self.store.check_readiness()
        self.assertEqual(result["status"], "incomplete")
        self.assertFalse(result["checks"]["papi_get_dashboard_snapshot"]["callable"])

if __name__ == "__main__":
    unittest.main()
