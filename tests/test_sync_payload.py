import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from papi_core.sync_bundle import build_sync_bundle
from papi_core.sync_payload import (
    SyncPayloadError, build_sync_payload, read_sync_payload,
    validate_sync_payload, write_sync_payload,
)

def digest(record):
    raw = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()

class SyncPayloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.agents = self.root / "agents.json"
        self.agents.write_text(json.dumps({"agents": [
            {"id": "agent-a", "name": "Agent A"}, {"id": "agent-b", "name": "Agent B"}
        ]}), encoding="utf-8")
        self.memory = {
            "event_id": "evt-memory-45", "event_type": "remember",
            "memory_id": "MEM-45-A", "created_at": "2026-11-14T10:00:00Z",
            "actor": "agent-a", "category": "fact", "title": "Procédure interne",
            "content": "Le traitement des commandes suit une validation humaine.",
            "source": {"type": "manual", "id": "doc-45"},
            "confidence": 0.9, "scope": "shared", "tags": ["process"],
            "sensitivity": "normal",
        }
        self.message = {
            "message_id": "MSG-0123456789ABCDEF0123456789ABCDEF",
            "sent_at": "2026-11-14T10:01:00Z", "sender": "agent-a",
            "recipient": "agent-b", "subject": "Coordination",
            "body": "Merci de vérifier le dossier de commandes avant validation.",
            "message_type": "task",
        }
        self.bundle = build_sync_bundle(
            source_instance_id="instance-a", destination_instance_id="instance-b",
            export_id="export-45", created_at="2026-11-14T10:02:00Z",
            cursor_start=1, cursor_end=2, events=[
                {"event_id": self.memory["event_id"], "kind": "memory",
                 "record_id": self.memory["memory_id"], "sequence": 1,
                 "content_digest": digest(self.memory)},
                {"event_id": self.message["message_id"], "kind": "message",
                 "record_id": self.message["message_id"], "sequence": 2,
                 "content_digest": digest(self.message)},
            ])
    def tearDown(self):
        self.temp.cleanup()
    def records(self):
        return [{"kind":"memory","record":self.memory},{"kind":"message","record":self.message}]
    def test_build_and_validate_mixed_payload(self):
        payload = build_sync_payload(bundle=self.bundle, records=self.records(), agents_path=self.agents)
        self.assertTrue(validate_sync_payload(payload, bundle=self.bundle, agents_path=self.agents))
        self.assertEqual(len(payload["records"]), 2)
    def test_payload_write_and_read_round_trip(self):
        result = write_sync_payload(bundle=self.bundle, records=self.records(),
                                    spool_dir=self.root/"spool", agents_path=self.agents)
        restored = read_sync_payload(Path(result["path"]), bundle=self.bundle, agents_path=self.agents)
        self.assertEqual(restored["payload_digest"], result["payload_digest"])
        self.assertEqual(Path(result["path"]).stat().st_mode & 0o777, 0o600)
    def test_content_tampering_rejected(self):
        changed = dict(self.memory, content="Contenu remplacé.")
        with self.assertRaises(SyncPayloadError):
            build_sync_payload(bundle=self.bundle,
                records=[{"kind":"memory","record":changed},{"kind":"message","record":self.message}],
                agents_path=self.agents)
    def test_private_or_restricted_memory_rejected(self):
        private = dict(self.memory, scope="agent")
        with self.assertRaises(SyncPayloadError):
            build_sync_payload(bundle=self.bundle,
                records=[{"kind":"memory","record":private},{"kind":"message","record":self.message}],
                agents_path=self.agents)
    def test_decision_memory_rejected(self):
        decision = dict(self.memory, category="decision")
        with self.assertRaises(SyncPayloadError):
            build_sync_payload(bundle=self.bundle,
                records=[{"kind":"memory","record":decision},{"kind":"message","record":self.message}],
                agents_path=self.agents)
    def test_personal_data_rejected(self):
        private_msg = dict(self.message, body="Contact: test@example.com")
        with self.assertRaises(SyncPayloadError):
            build_sync_payload(bundle=self.bundle,
                records=[{"kind":"memory","record":self.memory},{"kind":"message","record":private_msg}],
                agents_path=self.agents)
    def test_incomplete_or_duplicate_payload_rejected(self):
        with self.assertRaises(SyncPayloadError):
            build_sync_payload(bundle=self.bundle, records=self.records()[:1], agents_path=self.agents)
        with self.assertRaises(SyncPayloadError):
            build_sync_payload(bundle=self.bundle, records=[self.records()[0],self.records()[0]],
                               agents_path=self.agents)
    def test_payload_digest_tampering_rejected(self):
        payload = build_sync_payload(bundle=self.bundle, records=self.records(), agents_path=self.agents)
        payload["records"][0]["record"]["content"] = "altéré"
        with self.assertRaises(SyncPayloadError):
            validate_sync_payload(payload, bundle=self.bundle, agents_path=self.agents)
    def test_symlink_rejected(self):
        result = write_sync_payload(bundle=self.bundle, records=self.records(),
                                    spool_dir=self.root/"spool", agents_path=self.agents)
        link = self.root/"link.papidata"
        link.symlink_to(Path(result["path"]))
        with self.assertRaises(SyncPayloadError):
            read_sync_payload(link, bundle=self.bundle, agents_path=self.agents)

if __name__ == "__main__":
    unittest.main()
