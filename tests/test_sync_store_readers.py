import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from papi_core.chat import read_messages
from papi_core.memory import search_memory
from papi_core.principal import _issue_authenticated_agent_principal
from papi_core.sync_store import SyncStoreError, load_imported_records


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


class ImportedReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "imports.sqlite3"
        self.memory_file = self.root / "events.jsonl"
        self.chat_file = self.root / "messages.jsonl"
        self.agents = self.root / "agents.json"
        self.agents.write_text(json.dumps({"agents": [
            {"id": "agent-a", "name": "Agent A"},
            {"id": "agent-b", "name": "Agent B"}
        ]}), encoding="utf-8")
        self.principal = _issue_authenticated_agent_principal("agent-a")
        self.memory = {
            "event_id": "evt-imported-47", "event_type": "remember",
            "memory_id": "MEM-IMPORTED-47", "created_at": "2026-11-14T10:00:00Z",
            "actor": "agent-b", "category": "fact", "title": "Règle partagée",
            "content": "Toute action externe nécessite une validation humaine.",
            "source": {"type": "manual", "id": "doc-47"}, "confidence": 0.9,
            "scope": "shared", "tags": ["governance"], "sensitivity": "normal",
        }
        self.message = {
            "message_id": "MSG-0123456789ABCDEF0123456789ABCDEF",
            "sent_at": "2026-11-14T10:01:00Z", "sender": "agent-b",
            "recipient": "agent-a", "subject": "Transmission",
            "body": "Le rapport est prêt pour vérification.",
            "message_type": "report",
        }
        with sqlite3.connect(self.db) as db:
            db.executescript("""
                CREATE TABLE sync_import_batches (
                    bundle_digest TEXT PRIMARY KEY, payload_digest TEXT,
                    imported_at TEXT, record_count INTEGER
                );
                CREATE TABLE sync_bundle_receipts (
                    bundle_digest TEXT PRIMARY KEY, status TEXT
                );
                CREATE TABLE sync_bundle_receipt_items (
                    event_id TEXT, kind TEXT, record_id TEXT, content_digest TEXT,
                    bundle_digest TEXT
                );
                CREATE TABLE sync_imported_records (
                    event_id TEXT PRIMARY KEY, kind TEXT, record_id TEXT,
                    content_digest TEXT, record_json TEXT, bundle_digest TEXT
                );
            """)
            db.execute("INSERT INTO sync_import_batches VALUES (?,?,?,?)",
                       ("bundle-47", "payload-47", "2026-11-14T11:00:00Z", 2))
            db.execute("INSERT INTO sync_bundle_receipts VALUES (?,?)",
                       ("bundle-47", "verified_pending_manual_import"))
            for kind, record_id, record in (
                ("memory", self.memory["memory_id"], self.memory),
                ("message", self.message["message_id"], self.message),
            ):
                event_id = record["event_id"] if kind == "memory" else record["message_id"]
                content_digest = hashlib.sha256(canonical(record)).hexdigest()
                db.execute("INSERT INTO sync_bundle_receipt_items VALUES (?,?,?,?,?)",
                    (event_id, kind, record_id, content_digest, "bundle-47"))
                db.execute("INSERT INTO sync_imported_records VALUES (?,?,?,?,?,?)",
                    (event_id, kind, record_id, content_digest,
                     canonical(record).decode(), "bundle-47"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_memory_reader_includes_only_validated_shared_imports(self):
        result = search_memory(principal=self.principal, query="validation humaine",
                               path=self.memory_file, import_db=self.db)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["memory_id"], "MEM-IMPORTED-47")

    def test_chat_reader_includes_imported_messages_for_recipient(self):
        result = read_messages(recipient="agent-a", path=self.chat_file,
                               agents_path=self.agents, import_db=self.db)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["message_id"], self.message["message_id"])

    def test_chat_reader_excludes_other_recipients(self):
        result = read_messages(recipient="agent-b", path=self.chat_file,
                               agents_path=self.agents, import_db=self.db)
        self.assertEqual(result, [])

    def test_imported_content_digest_tampering_fails_closed(self):
        with sqlite3.connect(self.db) as db:
            db.execute("UPDATE sync_imported_records SET record_json=? WHERE kind='memory'",
                       (canonical({**self.memory, "content": "falsifié"}).decode(),))
        with self.assertRaises(SyncStoreError):
            load_imported_records(self.db, "memory")

    def test_memory_id_collision_with_local_journal_fails_closed(self):
        self.memory_file.write_text(json.dumps(self.memory, ensure_ascii=False) + "\n",
                                    encoding="utf-8")
        with self.assertRaises(ValueError):
            search_memory(principal=self.principal, path=self.memory_file, import_db=self.db)

    def test_missing_import_database_preserves_local_reader_behavior(self):
        result = search_memory(principal=self.principal, path=self.memory_file,
                               import_db=self.root / "not-created.sqlite3")
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
