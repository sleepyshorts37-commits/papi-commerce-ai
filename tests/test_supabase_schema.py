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
        self.assertIn("from public, anon, authenticated, service_role", self.sql)
        self.assertIn(
            "grant execute on function public.papi_consume_agent_nonce(text, integer, text, timestamptz)",
            self.sql,
        )

    def test_nonce_rpc_locks_the_active_key_during_consumption(self):
        match = re.search(
            r"create or replace function public\\.papi_consume_agent_nonce\\(.*?\\n\\$\\$;",
            self.sql, flags=re.IGNORECASE | re.DOTALL,
        )
        self.assertIsNotNone(match)
        body = match.group(0)
        self.assertIn("p_key_version", body)
        self.assertIn("status = 'active'", body)
        self.assertIn("for share", body.lower())
        self.assertLess(body.index("for share"), body.index("insert into public.papi_agent_used_nonces"))


if __name__ == "__main__":
    unittest.main()
