import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from papi_core.local_store import append_local_record, load_local_records
from papi_core.sqlite_backup import (
    BackupRestoreError, create_sqlite_backup, restore_sqlite_backup,
    verify_sqlite_backup,
)


class SQLiteBackupRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "journals.sqlite3"
        append_local_record(self.db, kind="memory", record_id="memory-1",
                            event_id="event-1", created_at="2026-11-14T12:00:00Z",
                            record={"memory_id": "memory-1", "content": "snapshot"})
        with sqlite3.connect(self.db) as connection:
            connection.execute("PRAGMA user_version=7")

    def tearDown(self):
        self.temp.cleanup()

    def test_backup_manifest_hash_and_integrity_verify(self):
        result = create_sqlite_backup(self.db, self.root / "backups")
        verified = verify_sqlite_backup(Path(result["manifest_path"]))
        self.assertEqual(result["status"], "backup_created")
        self.assertEqual(verified["status"], "verified")
        self.assertEqual(verified["sha256"], result["sha256"])
        self.assertEqual(verified["user_version"], 7)

    def test_restore_into_new_path_preserves_records_and_version(self):
        result = create_sqlite_backup(self.db, self.root / "backups")
        destination = self.root / "restored.sqlite3"
        restored = restore_sqlite_backup(Path(result["manifest_path"]), destination)
        self.assertEqual(restored["status"], "restored")
        self.assertEqual(load_local_records(destination, "memory")[0]["content"], "snapshot")
        with sqlite3.connect(destination) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 7)

    def test_restore_refuses_existing_destination_without_modifying_it(self):
        result = create_sqlite_backup(self.db, self.root / "backups")
        destination = self.root / "existing.sqlite3"
        destination.write_bytes(b"keep")
        with self.assertRaises(BackupRestoreError):
            restore_sqlite_backup(Path(result["manifest_path"]), destination)
        self.assertEqual(destination.read_bytes(), b"keep")

    def test_tampered_backup_digest_is_rejected(self):
        result = create_sqlite_backup(self.db, self.root / "backups")
        backup = Path(result["backup_path"])
        backup.write_bytes(backup.read_bytes() + b"tamper")
        with self.assertRaises(BackupRestoreError):
            verify_sqlite_backup(Path(result["manifest_path"]))

    def test_symlink_database_is_rejected(self):
        link = self.root / "linked.sqlite3"
        link.symlink_to(self.db)
        with self.assertRaises(BackupRestoreError):
            create_sqlite_backup(link, self.root / "backups")

    def test_manifest_version_boolean_is_rejected(self):
        result = create_sqlite_backup(self.db, self.root / "backups")
        manifest_path = Path(result["manifest_path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["format_version"] = True
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(BackupRestoreError):
            verify_sqlite_backup(manifest_path)


if __name__ == "__main__":
    unittest.main()
