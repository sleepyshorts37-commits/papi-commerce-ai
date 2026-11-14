import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from papi_core.chat import read_messages, send_message
from papi_core.local_store import LocalStoreError, append_local_record, load_local_records
from papi_core.memory import remember_fact, search_memory, supersede_memory
from papi_core.principal import _issue_authenticated_agent_principal


class SQLiteJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "journals.sqlite3"
        self.memory_jsonl = self.root / "memory.jsonl"
        self.chat_jsonl = self.root / "chat.jsonl"
        self.agents = self.root / "agents.json"
        self.agents.write_text(json.dumps({"agents": [
            {"id": "astou", "name": "Astou", "status": "active"},
            {"id": "marietou", "name": "Marietou", "status": "active"}
        ]}), encoding="utf-8")
        self.principal = _issue_authenticated_agent_principal("astou")

    def tearDown(self):
        self.temp.cleanup()

    def test_memory_sqlite_write_read_and_supersede(self):
        saved = remember_fact(
            principal=self.principal, category="fact", title="Stockage",
            content="La mémoire utilise SQLite local.", source_type="test",
            source_id="M48-1", path=self.memory_jsonl, sqlite_db=self.db,
        )
        found = search_memory(principal=self.principal, path=self.memory_jsonl, sqlite_db=self.db)
        self.assertEqual([item["memory_id"] for item in found], [saved["memory_id"]])
        self.assertTrue(supersede_memory(
            memory_id=saved["memory_id"], principal=self.principal,
            reason="Remplacée.", path=self.memory_jsonl, sqlite_db=self.db,
        ))
        self.assertEqual(search_memory(
            principal=self.principal, path=self.memory_jsonl, sqlite_db=self.db
        ), [])

    def test_chat_sqlite_write_and_read(self):
        sent = send_message(
            sender="astou", recipient="marietou", subject="SQLite",
            body="Message conservé localement.", path=self.chat_jsonl,
            agents_path=self.agents, sqlite_db=self.db,
        )
        received = read_messages(
            recipient="marietou", path=self.chat_jsonl,
            agents_path=self.agents, sqlite_db=self.db,
        )
        self.assertEqual([item["message_id"] for item in received], [sent["message_id"]])
        self.assertFalse(self.chat_jsonl.exists())

    def test_default_jsonl_behavior_is_unchanged(self):
        sent = send_message(sender="astou", recipient="all", subject="JSONL",
                            body="Compatibilité historique.", path=self.chat_jsonl,
                            agents_path=self.agents)
        self.assertEqual(read_messages(path=self.chat_jsonl, agents_path=self.agents), [sent])
        saved = remember_fact(principal=self.principal, category="fact", title="Legacy",
                              content="Le journal JSONL reste pris en charge.",
                              source_type="test", source_id="M48-2", path=self.memory_jsonl)
        self.assertEqual(search_memory(principal=self.principal, path=self.memory_jsonl)[0]["memory_id"],
                         saved["memory_id"])

    def test_append_only_and_duplicate_rejected(self):
        record = {"event_id": "event-1", "event_type": "supersede",
                  "target_memory_id": "mem-1", "created_at": "2026-11-14T00:00:00Z",
                  "actor": "astou", "reason": "test"}
        append_local_record(self.db, kind="memory", record_id="event-1",
                            event_id="event-1", created_at=record["created_at"], record=record)
        with self.assertRaises(LocalStoreError):
            append_local_record(self.db, kind="memory", record_id="event-1",
                                event_id="event-1", created_at=record["created_at"], record=record)
        with sqlite3.connect(self.db) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM local_journal_records WHERE record_id='event-1'")

    def test_symlink_database_rejected(self):
        real = self.root / "real.sqlite3"
        real.touch()
        link = self.root / "link.sqlite3"
        link.symlink_to(real)
        with self.assertRaises(LocalStoreError):
            append_local_record(link, kind="message", record_id="m1",
                                event_id="m1", created_at="2026-11-14T00:00:00Z",
                                record={"message_id": "m1"})


if __name__ == "__main__":
    unittest.main()
