"""Contrats de la migration partagée mémoire et PAPI CHAT."""
from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]
MIGRATION = ROOT / "infra" / "supabase" / "migrations" / "004_shared_collaboration.sql"
ROLLBACK = MIGRATION.with_name("004_shared_collaboration_down.sql")


class SharedCollaborationMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION.read_text(encoding="utf-8").lower()
        cls.down = ROLLBACK.read_text(encoding="utf-8").lower()

    def test_memory_events_are_bounded_and_scoped(self):
        self.assertIn("create table if not exists public.papi_memory_events", self.sql)
        self.assertIn("event_type in ('remember', 'supersede')", self.sql)
        self.assertIn("scope in ('shared', 'agent')", self.sql)
        self.assertIn("sensitivity = 'normal'", self.sql)
        self.assertIn("cardinality(tags) <= 10", self.sql)

    def test_chat_messages_are_bounded_and_typed(self):
        self.assertIn("create table if not exists public.papi_chat_messages", self.sql)
        self.assertIn("length(subject) between 1 and 120", self.sql)
        self.assertIn("length(body) between 1 and 2000", self.sql)
        self.assertIn("message_type in ('info', 'task', 'alert', 'report')", self.sql)

    def test_tables_are_server_role_only_and_rls_enabled(self):
        for table in ("papi_memory_events", "papi_chat_messages"):
            self.assertIn(f"alter table public.{table} enable row level security", self.sql)
            self.assertIn(f"revoke all on public.{table} from public, anon, authenticated", self.sql)
            self.assertIn(f"grant select, insert on public.{table} to service_role", self.sql)

    def test_append_only_guard_blocks_update_and_delete(self):
        self.assertEqual(self.sql.count("create or replace function public.papi_reject_append_only_mutation()"), 1)
        self.assertIn("before update or delete on public.papi_memory_events", self.sql)
        self.assertIn("before update or delete on public.papi_chat_messages", self.sql)
        self.assertIn("using errcode = '55000'", self.sql)

    def test_rollback_is_guarded_and_removes_only_empty_schema(self):
        self.assertIn("cannot rollback shared collaboration migration with retained data", self.down)
        self.assertIn("if exists (select 1 from public.papi_memory_events)", self.down)
        self.assertIn("drop table if exists public.papi_memory_events", self.down)
        self.assertIn("drop table if exists public.papi_chat_messages", self.down)


if __name__ == "__main__":
    unittest.main()
