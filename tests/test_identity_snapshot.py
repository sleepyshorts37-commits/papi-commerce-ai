import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from papi_core.identity_snapshot import (
    IdentitySnapshotError, load_ledger_snapshot, load_registry_snapshot,
    reconcile_identity_sources,
)


class IdentitySnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = self.root / "agents.json"
        self.database = self.root / "identity.sqlite"

    def tearDown(self):
        self.temp.cleanup()

    def create_registry(self):
        self.registry.write_text(json.dumps({
            "project": "PAPI COMMERCE AI",
            "agents": [{"id": "agent-a", "status": "active",
                        "permissions": ["read"], "prohibited": ["spend"]}],
        }), encoding="utf-8")

    def create_database(self):
        db = sqlite3.connect(self.database)
        db.execute("""CREATE TABLE identity_state (
            agent_id TEXT PRIMARY KEY, status TEXT NOT NULL,
            revision INTEGER NOT NULL, key_version INTEGER NOT NULL,
            permissions_json TEXT NOT NULL, prohibited_json TEXT NOT NULL,
            updated_at INTEGER NOT NULL)""")
        db.execute("INSERT INTO identity_state VALUES (?,?,?,?,?,?,?)",
                   ("agent-a", "active", 1, 1, '["read"]', '["spend"]', 1))
        db.commit()
        db.close()

    def test_registry_snapshot(self):
        self.create_registry()
        self.assertEqual(load_registry_snapshot(self.registry)[0]["id"], "agent-a")

    def test_registry_rejects_invalid_root(self):
        self.registry.write_text('{"agents":{}}', encoding="utf-8")
        with self.assertRaises(IdentitySnapshotError):
            load_registry_snapshot(self.registry)

    def test_registry_rejects_symlink(self):
        target = self.root / "target.json"
        target.write_text('{"agents":[]}', encoding="utf-8")
        self.registry.symlink_to(target)
        with self.assertRaises(IdentitySnapshotError):
            load_registry_snapshot(self.registry)

    def test_ledger_read_only_snapshot(self):
        self.create_database()
        before = self.database.read_bytes()
        rows = load_ledger_snapshot(self.database)
        self.assertEqual(rows[0]["agent_id"], "agent-a")
        self.assertEqual(self.database.read_bytes(), before)

    def test_missing_database_is_not_created(self):
        missing = self.root / "missing.sqlite"
        with self.assertRaises(IdentitySnapshotError):
            load_ledger_snapshot(missing)
        self.assertFalse(missing.exists())

    def test_incomplete_schema_fails_closed(self):
        db = sqlite3.connect(self.database)
        db.execute("CREATE TABLE identity_state (agent_id TEXT)")
        db.commit()
        db.close()
        with self.assertRaises(IdentitySnapshotError):
            load_ledger_snapshot(self.database)

    def test_integrated_reconciliation(self):
        self.create_registry()
        self.create_database()
        report = reconcile_identity_sources(self.registry, self.database)
        self.assertTrue(report["consistent"])
        self.assertEqual(report["registry_count"], 1)
        self.assertEqual(report["ledger_count"], 1)

    def test_sources_are_not_modified(self):
        self.create_registry()
        self.create_database()
        registry_before = self.registry.read_bytes()
        database_before = self.database.read_bytes()
        reconcile_identity_sources(self.registry, self.database)
        self.assertEqual(self.registry.read_bytes(), registry_before)
        self.assertEqual(self.database.read_bytes(), database_before)


if __name__ == "__main__":
    unittest.main()
