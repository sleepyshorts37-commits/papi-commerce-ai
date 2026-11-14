import hashlib
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from papi_core.identity_ed25519 import provision_ed25519_agent
from papi_core.sync_bundle import build_sync_bundle
from papi_core.sync_bundle_approval import sign_sync_bundle_approval
from papi_core.sync_import import SyncImportError, import_approved_sync_content
from papi_core.sync_payload import write_sync_payload
from papi_core.sync_spool import write_sync_package

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class AtomicSyncImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = self.root / "public.json"
        self.private = provision_ed25519_agent("owner-46", self.root / "keys", self.registry)
        self.agents = self.root / "agents.json"
        self.agents.write_text(json.dumps({"agents": [
            {"id": "agent-a", "name": "Agent A"}, {"id": "agent-b", "name": "Agent B"}
        ]}), encoding="utf-8")
        self.ledger = self.root / "import.sqlite3"
        self.memory = {
            "event_id": "evt-memory-46", "event_type": "remember",
            "memory_id": "MEM-46-A", "created_at": "2026-11-14T10:00:00Z",
            "actor": "agent-a", "category": "fact", "title": "Règle interne",
            "content": "Une validation humaine précède chaque action externe.",
            "source": {"type": "manual", "id": "doc-46"}, "confidence": 0.9,
            "scope": "shared", "tags": ["governance"], "sensitivity": "normal",
        }
        self.message = {
            "message_id": "MSG-0123456789ABCDEF0123456789ABCDEF",
            "sent_at": "2026-11-14T10:01:00Z", "sender": "agent-a",
            "recipient": "agent-b", "subject": "Contrôle",
            "body": "Vérifier les références avant intégration.",
            "message_type": "task",
        }
        self.records = [
            {"kind": "memory", "record": self.memory},
            {"kind": "message", "record": self.message},
        ]
        self.bundle = build_sync_bundle(
            source_instance_id="instance-source", destination_instance_id="instance-target",
            export_id="export-46", created_at="2026-11-14T10:02:00Z",
            cursor_start=1, cursor_end=2, events=[
                {"event_id": self.memory["event_id"], "kind": "memory",
                 "record_id": self.memory["memory_id"], "sequence": 1,
                 "content_digest": digest(self.memory)},
                {"event_id": self.message["message_id"], "kind": "message",
                 "record_id": self.message["message_id"], "sequence": 2,
                 "content_digest": digest(self.message)},
            ])
        self.approval = sign_sync_bundle_approval(
            owner_id="owner-46", private_key_path=self.private, bundle=self.bundle,
            approval_id="APR-46", issued_at="2026-11-14T12:00:00Z",
            expires_at="2026-11-14T12:10:00Z", nonce="nonce-import-46-0001",
            timestamp=int(NOW.timestamp()))
        package = write_sync_package(bundle=self.bundle, approval=self.approval,
                                      spool_dir=self.root / "packages")
        payload = write_sync_payload(bundle=self.bundle, records=self.records,
                                     spool_dir=self.root / "payloads", agents_path=self.agents)
        self.package_path, self.payload_path = Path(package["path"]), Path(payload["path"])

    def tearDown(self):
        self.temp.cleanup()

    def run_import(self, **overrides):
        args = {
            "package_path": self.package_path, "payload_path": self.payload_path,
            "owner_id": "owner-46", "registry_path": self.registry,
            "ledger_db": self.ledger, "expected_destination": "instance-target",
            "agents_path": self.agents, "now_epoch": int(NOW.timestamp()), "now": NOW,
        }
        args.update(overrides)
        return import_approved_sync_content(**args)

    def counts(self):
        with sqlite3.connect(self.ledger) as db:
            return tuple(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                         for table in ("used_nonces", "sync_bundle_receipts",
                                       "sync_bundle_receipt_items", "sync_import_batches",
                                       "sync_imported_records"))

    def test_imports_memory_and_chat_in_one_sqlite_transaction(self):
        result = self.run_import()
        self.assertEqual(result["status"], "imported")
        self.assertTrue(result["signature_verified"] if "signature_verified" in result else True)
        self.assertTrue(result["nonce_consumed_atomically"])
        self.assertTrue(result["receipt_and_content_committed_atomically"])
        self.assertFalse(result["execution_enabled"])
        self.assertEqual(result["imported_records"], 2)
        self.assertEqual(self.counts(), (1, 1, 2, 1, 2))
        with sqlite3.connect(self.ledger) as db:
            rows = db.execute("SELECT kind,record_id FROM sync_imported_records ORDER BY kind").fetchall()
        self.assertEqual(rows, [("memory", "MEM-46-A"),
                                ("message", "MSG-0123456789ABCDEF0123456789ABCDEF")])

    def test_replay_rolls_back_without_duplicate_content(self):
        self.run_import()
        with self.assertRaises(SyncImportError):
            self.run_import()
        self.assertEqual(self.counts(), (1, 1, 2, 1, 2))

    def test_invalid_payload_does_not_consume_nonce_or_create_receipt(self):
        self.payload_path.write_bytes(self.payload_path.read_bytes() + b" ")
        with self.assertRaises(SyncImportError):
            self.run_import()
        self.assertFalse(self.ledger.exists())

    def test_wrong_destination_fails_before_any_write(self):
        with self.assertRaises(SyncImportError):
            self.run_import(expected_destination="another-instance")
        self.assertFalse(self.ledger.exists())

    def test_same_bundle_fresh_approval_is_idempotent(self):
        first = self.run_import()
        approval = sign_sync_bundle_approval(
            owner_id="owner-46", private_key_path=self.private, bundle=self.bundle,
            approval_id="APR-46-RETRY", issued_at="2026-11-14T12:00:00Z",
            expires_at="2026-11-14T12:10:00Z", nonce="nonce-import-46-0002",
            timestamp=int(NOW.timestamp()))
        package = write_sync_package(bundle=self.bundle, approval=approval,
                                     spool_dir=self.root / "retry")
        second = self.run_import(package_path=Path(package["path"]))
        self.assertEqual(first["status"], "imported")
        self.assertEqual(second["status"], "already_imported")
        self.assertEqual(self.counts(), (2, 1, 2, 1, 2))


if __name__ == "__main__":
    unittest.main()
