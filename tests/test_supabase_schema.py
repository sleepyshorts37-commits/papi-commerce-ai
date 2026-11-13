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

    def test_lease_renewal_rejects_null_and_blank_inputs(self):
        match = re.search(
            r"create or replace function public\.papi_renew_job_lease\(.*?\n\$lease\$;",
            self.sql,
            flags=re.IGNORECASE | re.DOTALL,
        )
        self.assertIsNotNone(match, "papi_renew_job_lease definition must exist")
        body = match.group(0)
        self.assertIn("length(trim(p_job_id)) = 0", body)
        self.assertIn("length(trim(p_worker_id)) = 0", body)
        self.assertIn("p_lease_seconds is null", body)
        self.assertIn("p_lease_seconds < 15", body)
        self.assertIn("p_lease_seconds > 900", body)

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



    def test_external_audit_anchor_store_is_immutable_and_service_role_only(self):
        self.assertIn("create table if not exists public.papi_audit_anchor_records", self.sql)
        self.assertIn("create table if not exists public.papi_audit_anchor_heads", self.sql)
        self.assertIn("before update or delete on public.papi_audit_anchor_records", self.sql)
        self.assertIn(
            "revoke all on public.papi_audit_anchor_records from public, anon, authenticated",
            self.sql,
        )
        self.assertIn(
            "grant select, insert on public.papi_audit_anchor_records to service_role",
            self.sql,
        )
        self.assertIn(
            "grant execute on function public.papi_advance_audit_anchor(text, text, text) to service_role",
            self.sql,
        )

    def test_external_audit_anchor_uses_digest_validation_and_atomic_head_lock(self):
        match = re.search(
            r"create or replace function public\.papi_advance_audit_anchor\(.*?\n\$\$;",
            self.sql,
            flags=re.IGNORECASE | re.DOTALL,
        )
        self.assertIsNotNone(match, "papi_advance_audit_anchor definition must exist")
        body = match.group(0)
        self.assertIn("extensions.digest(pg_catalog.convert_to(v_canonical, 'UTF8'), 'sha256')", body)
        self.assertIn("for update", body.lower())
        self.assertIn("v_current.latest_record_digest is distinct from p_expected_digest", body)
        self.assertIn("v_sequence <= v_current.sequence", body)
        self.assertIn("set search_path = pg_catalog, public, extensions, pg_temp", body)
        self.assertIn("v_record->>'schema_version'", body)
        self.assertIn("v_checkpoint->>'schema_version'", body)
        self.assertIn("v_key_id !~ '^[A-Za-z0-9_.:-]{1,120}
if __name__ == "__main__":
    unittest.main()
", body)
        self.assertIn("v_signature is null", body)
        self.assertIn("record contains unknown fields", body)
        self.assertIn("record is missing required fields", body)
        self.assertIn("v_checkpoint ?& array['schema_version', 'sequence', 'head_hash']", body)
        self.assertNotIn("set search_path = public, extensions, pg_temp", body)

if __name__ == "__main__":
    unittest.main()
