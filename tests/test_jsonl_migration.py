import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from papi_core.chat import send_message
from papi_core.jsonl_migration import MigrationError, migrate_jsonl_to_sqlite
from papi_core.local_store import load_local_records
from papi_core.registry import AGENTS_FILE, load_agents


class JsonlMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "local.sqlite3"
        self.backups = self.root / "backups"
        self.agents = AGENTS_FILE
        self.agent_id = next(iter(load_agents(self.agents)))

    def tearDown(self):
        self.temp.cleanup()

    def _memory_journal(self, path):
        event = {
            "event_id": str(uuid4()), "event_type": "remember",
            "memory_id": str(uuid4()), "created_at": "2026-11-14T10:00:00Z",
            "actor": self.agent_id, "category": "fact", "title": "Migration",
            "content": "Entrée historique de test.", "source": {"type": "test", "id": "M49"},
            "confidence": 0.9, "scope": "shared", "tags": ["migration"],
            "sensitivity": "normal",
        }
        path.write_text(json.dumps(event, ensure_ascii=False) + "\n", encoding="utf-8")
        return event

    def test_memory_migration_backup_hash_and_source_preserved(self):
        source = self.root / "memory.jsonl"
        event = self._memory_journal(source)
        original = source.read_bytes()
        result = migrate_jsonl_to_sqlite(kind="memory", source_path=source,
                                         database_path=self.db, backup_dir=self.backups,
                                         agents_path=self.agents)
        self.assertEqual(result["status"], "migrated")
        self.assertEqual(result["record_count"], 1)
        self.assertEqual(hashlib.sha256(Path(result["backup_path"]).read_bytes()).hexdigest(),
                         hashlib.sha256(original).hexdigest())
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(load_local_records(self.db, "memory"), [event])

    def test_chat_migration_validates_and_preserves_source(self):
        source = self.root / "chat.jsonl"
        sent = send_message(sender=self.agent_id, recipient="all", subject="Archive",
                            body="Message historique.", path=source, agents_path=self.agents)
        original = source.read_bytes()
        result = migrate_jsonl_to_sqlite(kind="message", source_path=source,
                                         database_path=self.db, backup_dir=self.backups,
                                         agents_path=self.agents)
        self.assertEqual(result["record_count"], 1)
        self.assertEqual(load_local_records(self.db, "message"), [sent])
        self.assertEqual(source.read_bytes(), original)

    def test_identical_rerun_is_idempotent(self):
        source = self.root / "memory.jsonl"
        self._memory_journal(source)
        first = migrate_jsonl_to_sqlite(kind="memory", source_path=source,
                                        database_path=self.db, backup_dir=self.backups,
                                        agents_path=self.agents)
        second = migrate_jsonl_to_sqlite(kind="memory", source_path=source,
                                         database_path=self.db, backup_dir=self.backups,
                                         agents_path=self.agents)
        self.assertEqual(first["status"], "migrated")
        self.assertEqual(second["status"], "already_migrated")
        self.assertEqual(len(load_local_records(self.db, "memory")), 1)

    def test_invalid_jsonl_fails_before_database_creation(self):
        source = self.root / "bad.jsonl"
        source.write_text("{broken\n", encoding="utf-8")
        with self.assertRaises(MigrationError):
            migrate_jsonl_to_sqlite(kind="memory", source_path=source,
                                    database_path=self.db, backup_dir=self.backups,
                                    agents_path=self.agents)
        self.assertFalse(self.db.exists())

    def test_duplicate_chat_ids_rejected_before_database_creation(self):
        source = self.root / "duplicate.jsonl"
        sent = send_message(sender=self.agent_id, recipient="all", subject="Dup",
                            body="Same message.", path=self.root / "seed.jsonl",
                            agents_path=self.agents)
        source.write_text((json.dumps(sent) + "\n") * 2, encoding="utf-8")
        with self.assertRaises(MigrationError):
            migrate_jsonl_to_sqlite(kind="message", source_path=source,
                                    database_path=self.db, backup_dir=self.backups,
                                    agents_path=self.agents)
        self.assertFalse(self.db.exists())

    def test_conflict_rolls_back_whole_batch_and_migration_marker(self):
        source = self.root / "memory.jsonl"
        event = self._memory_journal(source)
        with sqlite3.connect(self.db) as db:
            db.execute("""CREATE TABLE local_journal_records (
                kind TEXT NOT NULL, record_id TEXT NOT NULL, event_id TEXT NOT NULL,
                created_at TEXT NOT NULL, record_json TEXT NOT NULL,
                PRIMARY KEY(kind, record_id), UNIQUE(kind, event_id))""")
            db.execute("INSERT INTO local_journal_records VALUES (?,?,?,?,?)",
                       ("memory", event["memory_id"], "other-event",
                        event["created_at"], json.dumps({"different": True})))
        with self.assertRaises(MigrationError):
            migrate_jsonl_to_sqlite(kind="memory", source_path=source,
                                    database_path=self.db, backup_dir=self.backups,
                                    agents_path=self.agents)
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM local_journal_records").fetchone()[0], 1)
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='jsonl_migration_runs'"
            ).fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM jsonl_migration_runs").fetchone()[0], 0)

    def test_symlink_source_rejected(self):
        real = self.root / "real.jsonl"
        self._memory_journal(real)
        link = self.root / "linked.jsonl"
        link.symlink_to(real)
        with self.assertRaises(MigrationError):
            migrate_jsonl_to_sqlite(kind="memory", source_path=link,
                                    database_path=self.db, backup_dir=self.backups,
                                    agents_path=self.agents)


if __name__ == "__main__":
    unittest.main()
