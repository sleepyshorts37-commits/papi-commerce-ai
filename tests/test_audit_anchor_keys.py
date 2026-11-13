"""Tests for the local Ed25519 audit signing-key lifecycle."""
import json
import os
import tempfile
import unittest
from pathlib import Path

from papi_core.audit_anchor_keys import AuditKeyError, LocalAuditKeyring


class AuditAnchorKeyringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "keyring"
        self.keyring = LocalAuditKeyring(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_provision_sign_and_verify(self):
        key_id = self.keyring.provision()
        message = b"canonical audit checkpoint payload"
        signature = self.keyring.sign(key_id, message)
        self.assertEqual(len(signature), 128)
        self.assertTrue(self.keyring.verify(key_id, message, signature))
        self.assertFalse(self.keyring.verify(key_id, message + b"x", signature))

    def test_rotation_retains_historical_public_key_for_verification(self):
        old_id = self.keyring.provision()
        message = b"historical checkpoint"
        old_signature = self.keyring.sign(old_id, message)
        new_id = self.keyring.rotate(old_id)
        self.assertNotEqual(old_id, new_id)
        self.assertTrue(self.keyring.verify(old_id, message, old_signature))
        self.assertFalse(self.keyring.verify(old_id, message, self.keyring.sign(new_id, message)))
        self.assertTrue(self.keyring.verify(new_id, message, self.keyring.sign(new_id, message)))
        with self.assertRaises(AuditKeyError):
            self.keyring.sign(old_id, message)

    def test_revocation_blocks_historical_verification_and_signing(self):
        key_id = self.keyring.provision()
        message = b"record signed before revocation"
        signature = self.keyring.sign(key_id, message)
        self.keyring.revoke(key_id)
        self.assertFalse(self.keyring.verify(key_id, message, signature))
        with self.assertRaises(AuditKeyError):
            self.keyring.sign(key_id, message)

    def test_unknown_and_malformed_key_ids_fail_closed(self):
        self.keyring.provision()
        self.assertFalse(self.keyring.verify("unknown", b"x", "00" * 64))
        self.assertFalse(self.keyring.verify("../private", b"x", "00" * 64))

    def test_corrupt_registry_fails_closed(self):
        self.keyring.provision()
        self.keyring.registry_path.write_text('{"schema_version":1,"keys":null}', encoding="utf-8")
        with self.assertRaises(AuditKeyError):
            self.keyring.sign("audit-" + "0" * 32, b"x")
        with self.assertRaises(AuditKeyError):
            self.keyring.rotate("audit-" + "0" * 32)


    def test_registry_with_unhashable_status_fails_closed(self):
        key_id = self.keyring.provision()
        data = json.loads(self.keyring.registry_path.read_text(encoding="utf-8"))
        data["keys"][key_id]["status"] = []
        self.keyring.registry_path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(AuditKeyError):
            self.keyring.verify(key_id, b"x", "00" * 64)

    def test_private_key_permissions_are_restrictive(self):
        key_id = self.keyring.provision()
        private_path = self.root / "private" / (key_id + ".pem")
        self.assertEqual(private_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.root / "private").stat().st_mode & 0o777, 0o700)
        os.chmod(private_path, 0o644)
        with self.assertRaises(AuditKeyError):
            self.keyring.sign(key_id, b"x")


    def test_private_key_symlink_is_rejected(self):
        key_id = self.keyring.provision()
        private_path = self.root / "private" / (key_id + ".pem")
        target = self.root / "external.pem"
        target.write_bytes(private_path.read_bytes())
        os.chmod(target, 0o600)
        private_path.unlink()
        private_path.symlink_to(target)
        with self.assertRaises(AuditKeyError):
            self.keyring.sign(key_id, b"x")

    def test_private_public_key_mismatch_is_detected(self):
        key_id = self.keyring.provision()
        private_path = self.root / "private" / (key_id + ".pem")
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        other = Ed25519PrivateKey.generate()
        private_path.write_bytes(other.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()
        ))
        os.chmod(private_path, 0o600)
        with self.assertRaises(AuditKeyError):
            self.keyring.sign(key_id, b"x")

    def test_only_one_active_key_is_permitted(self):
        key_id = self.keyring.provision()
        data = json.loads(self.keyring.registry_path.read_text(encoding="utf-8"))
        data["keys"]["audit-" + "1" * 32] = dict(data["keys"][key_id])
        self.keyring.registry_path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(AuditKeyError):
            self.keyring.sign(key_id, b"x")

    def test_rotation_requires_current_active_key(self):
        key_id = self.keyring.provision()
        self.keyring.rotate(key_id)
        with self.assertRaises(AuditKeyError):
            self.keyring.rotate(key_id)


class AuditAnchorEd25519IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.journal = self.root / "audit.jsonl"
        self.keyring = LocalAuditKeyring(self.root / "keyring")
        self.store = _MemoryAnchorStore()
        self.journal_id = "ed25519-audit-test"

    def tearDown(self):
        self.temp.cleanup()

    def _add_event(self, event_id):
        from papi_core.audit import append_event, new_event
        append_event(new_event(
            event_id=event_id, actor="test:system", action="test.checkpoint",
            entity_type="test", entity_id=event_id, details={"safe": True},
        ), self.journal)

    def _record(self, previous, key_id):
        from papi_core.audit_anchor import canonical_record_bytes
        from papi_core.audit_checkpoint import build_checkpoint
        unsigned = {
            "schema_version": 1, "journal_id": self.journal_id,
            "checkpoint": build_checkpoint(self.journal),
            "previous_record_digest": previous, "key_id": key_id,
        }
        payload = canonical_record_bytes(unsigned)
        return {**unsigned, "signature": self.keyring.sign(key_id, payload)}

    def _publish(self, record):
        from papi_core.audit_anchor import publish_checkpoint_record
        return publish_checkpoint_record(
            journal_path=self.journal, journal_id=self.journal_id,
            record=record, store=self.store, verify_signature=self.keyring.verify,
        )

    def test_rotation_keeps_old_anchor_verifiable_and_new_key_signs_successor(self):
        from papi_core.audit_anchor import verify_checkpoint_anchor
        old_key = self.keyring.provision()
        self._add_event("ed25519-evt-1")
        first = self._publish(self._record(None, old_key))
        new_key = self.keyring.rotate(old_key)
        self._add_event("ed25519-evt-2")
        second = self._publish(self._record(first, new_key))
        self.assertNotEqual(first, second)
        result = verify_checkpoint_anchor(
            journal_path=self.journal, journal_id=self.journal_id,
            store=self.store, verify_signature=self.keyring.verify,
        )
        self.assertTrue(result["anchored"])
        self.assertEqual(result["latest_digest"], second)
        self.assertTrue(self.keyring.verify(
            old_key,
            __import__("papi_core.audit_anchor", fromlist=["_unsigned_payload"])._unsigned_payload(
                __import__("json").loads(self.store.records[first].decode("utf-8"))
            ),
            __import__("json").loads(self.store.records[first].decode("utf-8"))["signature"],
        ))

    def test_revoked_historical_key_invalidates_chain_verification(self):
        from papi_core.audit_anchor import CheckpointAnchorError, verify_checkpoint_anchor
        old_key = self.keyring.provision()
        self._add_event("ed25519-revoke-evt-1")
        first = self._publish(self._record(None, old_key))
        new_key = self.keyring.rotate(old_key)
        self._add_event("ed25519-revoke-evt-2")
        self._publish(self._record(first, new_key))
        self.keyring.revoke(old_key)
        with self.assertRaises(CheckpointAnchorError):
            verify_checkpoint_anchor(
                journal_path=self.journal, journal_id=self.journal_id,
                store=self.store, verify_signature=self.keyring.verify,
            )


class _MemoryAnchorStore:
    def __init__(self):
        self.records = {}
        self.latest = {}

    def get_latest(self, journal_id):
        return self.latest.get(journal_id)

    def get_record(self, digest):
        return self.records.get(digest)

    def put_record(self, digest, payload):
        if digest in self.records and self.records[digest] != payload:
            raise AssertionError("immutable record changed")
        self.records[digest] = payload

    def compare_and_swap_latest(self, journal_id, expected, new_digest):
        if self.latest.get(journal_id) != expected or new_digest not in self.records:
            return False
        self.latest[journal_id] = new_digest
        return True


class AuditAnchorEd25519IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.journal = self.root / "audit.jsonl"
        self.keyring = LocalAuditKeyring(self.root / "keyring")
        self.store = _MemoryAnchorStore()
        self.journal_id = "ed25519-audit-test"

    def tearDown(self):
        self.temp.cleanup()

    def _add_event(self, event_id):
        from papi_core.audit import append_event, new_event
        append_event(new_event(
            event_id=event_id, actor="test:system", action="test.checkpoint",
            entity_type="test", entity_id=event_id, details={"safe": True},
        ), self.journal)

    def _record(self, previous, key_id):
        from papi_core.audit_anchor import canonical_record_bytes
        from papi_core.audit_checkpoint import build_checkpoint
        unsigned = {
            "schema_version": 1, "journal_id": self.journal_id,
            "checkpoint": build_checkpoint(self.journal),
            "previous_record_digest": previous, "key_id": key_id,
        }
        return {**unsigned, "signature": self.keyring.sign(
            key_id, canonical_record_bytes(unsigned)
        )}

    def _publish(self, record):
        from papi_core.audit_anchor import publish_checkpoint_record
        return publish_checkpoint_record(
            journal_path=self.journal, journal_id=self.journal_id,
            record=record, store=self.store, verify_signature=self.keyring.verify,
        )

    def test_rotation_keeps_old_anchor_verifiable_and_new_key_signs_successor(self):
        from papi_core.audit_anchor import verify_checkpoint_anchor
        old_key = self.keyring.provision()
        self._add_event("ed25519-evt-1")
        first = self._publish(self._record(None, old_key))
        new_key = self.keyring.rotate(old_key)
        self._add_event("ed25519-evt-2")
        second = self._publish(self._record(first, new_key))
        result = verify_checkpoint_anchor(
            journal_path=self.journal, journal_id=self.journal_id,
            store=self.store, verify_signature=self.keyring.verify,
        )
        self.assertTrue(result["anchored"])
        self.assertEqual(result["latest_digest"], second)
        self.assertTrue(self.keyring.verify(
            old_key,
            __import__("papi_core.audit_anchor", fromlist=["_unsigned_payload"])._unsigned_payload(
                __import__("json").loads(self.store.records[first].decode("utf-8"))
            ),
            __import__("json").loads(self.store.records[first].decode("utf-8"))["signature"],
        ))

    def test_revoked_historical_key_invalidates_chain_verification(self):
        from papi_core.audit_anchor import CheckpointAnchorError, verify_checkpoint_anchor
        old_key = self.keyring.provision()
        self._add_event("ed25519-revoke-evt-1")
        first = self._publish(self._record(None, old_key))
        new_key = self.keyring.rotate(old_key)
        self._add_event("ed25519-revoke-evt-2")
        self._publish(self._record(first, new_key))
        self.keyring.revoke(old_key)
        with self.assertRaises(CheckpointAnchorError):
            verify_checkpoint_anchor(
                journal_path=self.journal, journal_id=self.journal_id,
                store=self.store, verify_signature=self.keyring.verify,
            )


class _MemoryAnchorStore:
    def __init__(self):
        self.records = {}
        self.latest = {}

    def get_latest(self, journal_id):
        return self.latest.get(journal_id)

    def get_record(self, digest):
        return self.records.get(digest)

    def put_record(self, digest, payload):
        if digest in self.records and self.records[digest] != payload:
            raise AssertionError("immutable record changed")
        self.records[digest] = payload

    def compare_and_swap_latest(self, journal_id, expected, new_digest):
        if self.latest.get(journal_id) != expected or new_digest not in self.records:
            return False
        self.latest[journal_id] = new_digest
        return True


class AuditAnchorEd25519IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.journal = self.root / "audit.jsonl"
        self.keyring = LocalAuditKeyring(self.root / "keyring")
        self.store = _MemoryAnchorStore()
        self.journal_id = "ed25519-audit-test"

    def tearDown(self):
        self.temp.cleanup()

    def _add_event(self, event_id):
        from papi_core.audit import append_event, new_event
        append_event(new_event(
            event_id=event_id, actor="test:system", action="test.checkpoint",
            entity_type="test", entity_id=event_id, details={"safe": True},
        ), self.journal)

    def _record(self, previous, key_id):
        from papi_core.audit_anchor import canonical_record_bytes
        from papi_core.audit_checkpoint import build_checkpoint
        unsigned = {
            "schema_version": 1, "journal_id": self.journal_id,
            "checkpoint": build_checkpoint(self.journal),
            "previous_record_digest": previous, "key_id": key_id,
        }
        return {**unsigned, "signature": self.keyring.sign(
            key_id, canonical_record_bytes(unsigned)
        )}

    def _publish(self, record):
        from papi_core.audit_anchor import publish_checkpoint_record
        return publish_checkpoint_record(
            journal_path=self.journal, journal_id=self.journal_id,
            record=record, store=self.store, verify_signature=self.keyring.verify,
        )

    def test_rotation_keeps_old_anchor_verifiable_and_new_key_signs_successor(self):
        from papi_core.audit_anchor import verify_checkpoint_anchor
        old_key = self.keyring.provision()
        self._add_event("ed25519-evt-1")
        first = self._publish(self._record(None, old_key))
        new_key = self.keyring.rotate(old_key)
        self._add_event("ed25519-evt-2")
        second = self._publish(self._record(first, new_key))
        result = verify_checkpoint_anchor(
            journal_path=self.journal, journal_id=self.journal_id,
            store=self.store, verify_signature=self.keyring.verify,
        )
        self.assertTrue(result["anchored"])
        self.assertEqual(result["latest_digest"], second)

    def test_revoked_historical_key_invalidates_chain_verification(self):
        from papi_core.audit_anchor import CheckpointAnchorError, verify_checkpoint_anchor
        old_key = self.keyring.provision()
        self._add_event("ed25519-revoke-evt-1")
        first = self._publish(self._record(None, old_key))
        new_key = self.keyring.rotate(old_key)
        self._add_event("ed25519-revoke-evt-2")
        self._publish(self._record(first, new_key))
        self.keyring.revoke(old_key)
        with self.assertRaises(CheckpointAnchorError):
            verify_checkpoint_anchor(
                journal_path=self.journal, journal_id=self.journal_id,
                store=self.store, verify_signature=self.keyring.verify,
            )


class _MemoryAnchorStore:
    def __init__(self):
        self.records = {}
        self.latest = {}

    def get_latest(self, journal_id):
        return self.latest.get(journal_id)

    def get_record(self, digest):
        return self.records.get(digest)

    def put_record(self, digest, payload):
        if digest in self.records and self.records[digest] != payload:
            raise AssertionError("immutable record changed")
        self.records[digest] = payload

    def compare_and_swap_latest(self, journal_id, expected, new_digest):
        if self.latest.get(journal_id) != expected or new_digest not in self.records:
            return False
        self.latest[journal_id] = new_digest
        return True


if __name__ == "__main__":
    unittest.main()
