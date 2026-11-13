"""Regression checks for the additive shared collaboration migration."""
from pathlib import Path
import unittest

MIGRATION = Path(__file__).parents[1] / "infra" / "supabase" / "migrations" / "004_shared_collaboration.sql"


class SharedCollaborationMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION.read_text(encoding="utf-8").lower()

    def test_memory_events_are_append_only_and_scoped(self):
        self.assertIn("create table if not exists public.papi_memory_events", self.sql)
        self.assertIn("event_type in ('remember', 'supersede')", self.sql)
        self.assertIn("scope in ('shared', 'agent')", self.sql)
        self.assertIn("sensitivity = 'normal'", self.sql)
        self.assertIn("before update or delete on public.papi_memory_events", self.sql)

    def test_chat_messages_are_append_only_and_bounded(self):
        self.assertIn("create table if not exists public.papi_chat_messages", self.sql)
        self.assertIn("length(subject) between 1 and 120", self.sql)
        self.assertIn("length(body) between 1 and 2000", self.sql)
        self.assertIn("before update or delete on public.papi_chat_messages", self.sql)

    def test_tables_are_server_role_only(self):
        for table in ("papi_memory_events", "papi_chat_messages"):
            self.assertIn(f"alter table public.{table} enable row level security", self.sql)
            self.assertIn(f"revoke all on public.{table} from public, anon, authenticated", self.sql)
            self.assertIn(f"grant select, insert on public.{table} to service_role", self.sql)

    def test_mutation_guard_is_shared_and_rejects_updates(self):
        self.assertEqual(self.sql.count("create or replace function public.papi_reject_append_only_mutation()"), 1)
        self.assertIn("raise exception 'append-only records cannot be changed'", self.sql)
        self.assertIn("using errcode = '55000'", self.sql)

    def test_rollback_refuses_to_delete_existing_shared_data(self):
        rollback = MIGRATION.with_name("004_shared_collaboration_down.sql").read_text(encoding="utf-8").lower()
        self.assertIn("cannot rollback shared collaboration migration with retained data", rollback)
        self.assertIn("if exists (select 1 from public.papi_memory_events)", rollback)
        self.assertIn("drop table if exists public.papi_memory_events", rollback)


if __name__ == "__main__":
    unittest.main()
