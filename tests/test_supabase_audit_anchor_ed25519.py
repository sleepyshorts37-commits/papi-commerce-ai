"""End-to-end Ed25519 + Supabase adapter contract tests.

The PostgREST transport is simulated; these tests prove application-layer
composition and failure handling, not availability or security of a live
Supabase project.
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote

from runtime.papi_core.audit import append_event, new_event
from runtime.papi_core.audit_anchor import (
    CheckpointAnchorError,
    CheckpointConflict,
    canonical_record_bytes,
    publish_checkpoint_record,
    verify_checkpoint_anchor,
)
from runtime.papi_core.audit_anchor_keys import LocalAuditKeyring
from runtime.papi_core.storage import StoreError, SupabaseStore
from runtime.papi_core.supabase_audit_anchor import SupabaseCheckpointStore


class PostgrestContractSimulator:
    """Small deterministic PostgREST/RPC simulator; never contacts Supabase."""

    def __init__(self):
        self.records = {}
        self.heads = {}
        self.fail_cas = False
        self.commit_then_timeout = False

    def request(self, method, path, payload=None, prefer=None):
        if method == "GET" and path.startswith("papi_audit_anchor_heads?"):
            journal_id = unquote(path.split("journal_id=eq.", 1)[1].split("&", 1)[0])
            digest = self.heads.get(journal_id)
            return [] if digest is None else [{"latest_record_digest": digest}]

        if method == "GET" and path.startswith("papi_audit_anchor_records?"):
            digest = path.split("record_digest=eq.", 1)[1].split("&", 1)[0]
            return [
                {"canonical_record": value["canonical_record"]}
                for (journal_id, record_digest), value in self.records.items()
                if record_digest == digest
            ]

        if method == "POST" and path.startswith("papi_audit_anchor_records?"):
            key = (payload["journal_id"], payload["record_digest"])
            existing = self.records.get(key)
            if existing is not None and existing["canonical_record"] != payload["canonical_record"]:
                raise StoreError("immutable record collision")
            self.records.setdefault(key, dict(payload))
            return None

        if method == "POST" and path == "rpc/papi_advance_audit_anchor":
            if self.fail_cas:
                return False
            journal_id = payload["p_journal_id"]
            expected = payload["p_expected_digest"]
            new_digest = payload["p_new_digest"]
            if self.heads.get(journal_id) != expected:
                return False
            if not any(digest == new_digest for _, digest in self.records):
                return False
            self.heads[journal_id] = new_digest
            if self.commit_then_timeout:
                self.commit_then_timeout = False
                raise TimeoutError("simulated lost response after remote commit")
            return True

        raise AssertionError(f"Unexpected PostgREST request: {method} {path}")


class SupabaseEd25519EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.journal = self.root / "audit.jsonl"
        self.journal_id = "end-to-end-audit"
        self.keyring = LocalAuditKeyring(self.root / "keyring")
        self.transport = PostgrestContractSimulator()
        client = object.__new__(SupabaseStore)
        client.request = self.transport.request
        self.store = SupabaseCheckpointStore(client, verify_signature=self.keyring.verify)

    def tearDown(self):
        self.temp.cleanup()

    def add_event(self, event_id):
        append_event(new_event(
            event_id=event_id, actor="test:backend", action="audit.integration",
            entity_type="test", entity_id=event_id, details={"safe": True},
        ), self.journal)

    def signed_record(self, previous_digest, key_id):
        from runtime.papi_core.audit_checkpoint import build_checkpoint
        unsigned = {
            "schema_version": 1,
            "journal_id": self.journal_id,
            "checkpoint": build_checkpoint(self.journal),
            "previous_record_digest": previous_digest,
            "key_id": key_id,
        }
        signature = self.keyring.sign(key_id, canonical_record_bytes(unsigned))
        return {**unsigned, "signature": signature}

    def publish(self, record):
        return publish_checkpoint_record(
            journal_path=self.journal,
            journal_id=self.journal_id,
            record=record,
            store=self.store,
            verify_signature=self.keyring.verify,
        )

    def verify(self):
        return verify_checkpoint_anchor(
            journal_path=self.journal,
            journal_id=self.journal_id,
            store=self.store,
            verify_signature=self.keyring.verify,
        )

    def test_ed25519_chain_survives_rotation_through_supabase_adapter(self):
        old_key = self.keyring.provision()
        self.add_event("anchor-event-1")
        first = self.publish(self.signed_record(None, old_key))

        new_key = self.keyring.rotate(old_key)
        self.add_event("anchor-event-2")
        second = self.publish(self.signed_record(first, new_key))

        verified = self.verify()
        self.assertTrue(verified["anchored"])
        self.assertEqual(verified["latest_digest"], second)
        self.assertNotEqual(first, second)
        self.assertEqual(self.store.get_latest(self.journal_id), second)

    def test_cas_conflict_does_not_advance_pointer(self):
        key_id = self.keyring.provision()
        self.add_event("anchor-conflict-event")
        self.transport.fail_cas = True
        with self.assertRaises(CheckpointConflict):
            self.publish(self.signed_record(None, key_id))
        self.assertIsNone(self.store.get_latest(self.journal_id))
        self.assertEqual(len(self.transport.records), 1)

    def test_retry_after_commit_response_timeout_is_idempotent(self):
        key_id = self.keyring.provision()
        self.add_event("anchor-timeout-event")
        record = self.signed_record(None, key_id)
        self.transport.commit_then_timeout = True
        with self.assertRaises(TimeoutError):
            self.publish(record)
        committed = self.store.get_latest(self.journal_id)
        self.assertIsInstance(committed, str)
        self.assertEqual(self.publish(record), committed)

    def test_tampered_signature_with_recomputed_record_digest_is_rejected(self):
        key_id = self.keyring.provision()
        self.add_event("anchor-tamper-event")
        digest = self.publish(self.signed_record(None, key_id))
        key = (self.journal_id, digest)
        record = json.loads(self.transport.records[key]["canonical_record"])
        record["signature"] = "00" * 64
        canonical = canonical_record_bytes(record)
        replacement_digest = hashlib.sha256(canonical).hexdigest()
        self.transport.records.pop(key)
        self.transport.records[(self.journal_id, replacement_digest)] = {
            "journal_id": self.journal_id,
            "record_digest": replacement_digest,
            "canonical_record": canonical.decode("utf-8"),
        }
        self.transport.heads[self.journal_id] = replacement_digest
        with self.assertRaises(CheckpointAnchorError):
            self.verify()


if __name__ == "__main__":
    unittest.main()
