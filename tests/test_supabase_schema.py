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


if __name__ == "__main__":
    unittest.main()
