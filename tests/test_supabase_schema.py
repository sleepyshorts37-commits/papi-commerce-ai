"""Regression checks for the Supabase PostgreSQL schema."""
from pathlib import Path
import re
import unittest


SCHEMA = Path(__file__).parents[1] / "infra" / "supabase" / "schema.sql"


class SupabaseSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = SCHEMA.read_text(encoding="utf-8")

    def test_dollar_quoted_function_bodies_are_balanced(self):
        self.assertEqual(self.sql.count("$$;"), self.sql.count("as $$"))

    def test_job_failure_function_has_valid_error_code_guard(self):
        match = re.search(
            r"create or replace function public\.papi_fail_job\(.*?\n\$\$;",
            self.sql,
            flags=re.IGNORECASE | re.DOTALL,
        )
        self.assertIsNotNone(match, "papi_fail_job definition must exist")
        body = match.group(0)
        self.assertIn("p_error_code !~ '^[a-z0-9_]{1,80}$' then", body)
        self.assertEqual(body.count("raise exception 'Invalid error code'"), 1)
        self.assertNotIn("\\n        raise exception", body)

    def test_security_rpc_is_defined_once_and_service_role_only(self):
        self.assertEqual(self.sql.count("create or replace function public.papi_consume_agent_nonce("), 1)
        self.assertIn(
            "revoke all on function public.papi_consume_agent_nonce(text, text, timestamptz)",
            self.sql,
        )
        self.assertIn(
            "grant execute on function public.papi_consume_agent_nonce(text, text, timestamptz)",
            self.sql,
        )


    def test_worker_store_tables_are_private_and_rls_protected(self):
        self.assertIn("create table if not exists public.papi_worker_records", self.sql)
        self.assertIn("create table if not exists public.papi_worker_event_receipts", self.sql)
        self.assertIn("alter table public.papi_worker_records enable row level security", self.sql)
        self.assertIn("alter table public.papi_worker_event_receipts enable row level security", self.sql)
        self.assertIn("revoke all on public.papi_worker_records from public, anon, authenticated", self.sql)
        self.assertIn("revoke all on public.papi_worker_event_receipts from public, anon, authenticated", self.sql)

    def test_worker_sync_rpc_is_invoker_only_and_idempotent(self):
        self.assertEqual(self.sql.count("create or replace function public.papi_sync_worker_record("), 1)
        self.assertIn("security invoker", self.sql.lower())
        self.assertIn("where idempotency_key = p_idempotency_key", self.sql)
        self.assertIn("v_receipt.payload is distinct from p_payload", self.sql)
        self.assertIn("grant execute on function public.papi_sync_worker_record(", self.sql)
        self.assertIn("to service_role;", self.sql)
        self.assertIn("using errcode = '40001'", self.sql)
        self.assertIn("pg_advisory_xact_lock(hashtextextended(p_idempotency_key, 0))", self.sql)

if __name__ == "__main__":
    unittest.main()
