import hashlib, sqlite3, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from papi_core.identity_ed25519 import provision_ed25519_agent
from papi_core.sync_bundle import build_sync_bundle
from papi_core.sync_bundle_approval import sign_sync_bundle_approval
from papi_core.sync_receipt_ledger import SyncReceiptLedgerError, record_verified_sync_bundle

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)
A, B = hashlib.sha256(b"synthetic-a").hexdigest(), hashlib.sha256(b"synthetic-b").hexdigest()

class SyncReceiptLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry, self.replay = self.root/"public.json", self.root/"replay.sqlite3"
        self.ledger = self.root/"receipts.sqlite3"
        self.private = provision_ed25519_agent("owner-41", self.root/"keys", self.registry)
    def tearDown(self): self.temp.cleanup()
    def bundle(self, export_id="export-41", events=None):
        events = events or [{"event_id":"evt-41-a","kind":"memory","record_id":"MEM-41-A",
            "sequence":1,"content_digest":A}]
        return build_sync_bundle(source_instance_id="instance-a", destination_instance_id="instance-b",
            export_id=export_id, created_at="2026-11-14T11:59:00Z",
            cursor_start=1, cursor_end=len(events), events=events)
    def signed(self, bundle, approval_id="APR-41", nonce="nonce-approval-41-0001"):
        return sign_sync_bundle_approval(owner_id="owner-41", private_key_path=self.private,
            bundle=bundle, approval_id=approval_id, issued_at="2026-11-14T12:00:00Z",
            expires_at="2026-11-14T12:10:00Z", nonce=nonce, timestamp=int(NOW.timestamp()))
    def record(self, bundle, envelope):
        return record_verified_sync_bundle(envelope=envelope, bundle=bundle, owner_id="owner-41",
            registry_path=self.registry, replay_db=self.replay, ledger_db=self.ledger,
            expected_destination="instance-b", now_epoch=int(NOW.timestamp()), now=NOW)
    def rows(self):
        with sqlite3.connect(self.ledger) as db:
            return db.execute("SELECT event_id FROM sync_bundle_receipt_items ORDER BY event_id").fetchall()
    def test_valid_approval_records_metadata_and_references_only(self):
        bundle=self.bundle(); result=self.record(bundle,self.signed(bundle))
        self.assertEqual(result["status"],"recorded")
        self.assertTrue(result["receipt_committed"]); self.assertFalse(result["import_performed"])
        self.assertEqual(self.rows(),[("evt-41-a",)])
    def test_same_bundle_is_idempotent_with_new_approval_nonce(self):
        bundle=self.bundle(); self.record(bundle,self.signed(bundle))
        result=self.record(bundle,self.signed(bundle,"APR-41-RETRY","nonce-approval-41-0002"))
        self.assertEqual(result["status"],"already_recorded"); self.assertEqual(len(self.rows()),1)
    def test_conflicting_event_id_rejected_without_partial_write(self):
        first=self.bundle(); self.record(first,self.signed(first))
        second=self.bundle("export-41-b",[
            {"event_id":"evt-41-b-new","kind":"memory","record_id":"MEM-41-B","sequence":1,"content_digest":B},
            {"event_id":"evt-41-a","kind":"memory","record_id":"MEM-41-C","sequence":2,"content_digest":B}])
        with self.assertRaises(SyncReceiptLedgerError):
            self.record(second,self.signed(second,"APR-41-B","nonce-approval-41-0003"))
        self.assertEqual(self.rows(),[("evt-41-a",)])
    def test_conflicting_resource_reference_rejected(self):
        first=self.bundle(); self.record(first,self.signed(first))
        second=self.bundle("export-41-c",[{"event_id":"evt-41-c","kind":"memory",
            "record_id":"MEM-41-A","sequence":1,"content_digest":B}])
        with self.assertRaises(SyncReceiptLedgerError):
            self.record(second,self.signed(second,"APR-41-C","nonce-approval-41-0004"))
        self.assertEqual(self.rows(),[("evt-41-a",)])
    def test_wrong_destination_and_tampered_bundle_rejected(self):
        bundle=self.bundle(); envelope=self.signed(bundle)
        with self.assertRaises(SyncReceiptLedgerError):
            record_verified_sync_bundle(envelope=envelope,bundle=bundle,owner_id="owner-41",
                registry_path=self.registry,replay_db=self.replay,ledger_db=self.ledger,
                expected_destination="instance-c",now_epoch=int(NOW.timestamp()),now=NOW)
        altered=dict(bundle); altered["export_id"]="tampered"
        with self.assertRaises(SyncReceiptLedgerError): self.record(altered,self.signed(bundle,nonce="nonce-approval-41-0005"))
        self.assertFalse(self.ledger.exists())
    def test_replayed_approval_rejected(self):
        bundle=self.bundle(); envelope=self.signed(bundle); self.record(bundle,envelope)
        with self.assertRaises(SyncReceiptLedgerError): self.record(bundle,envelope)

if __name__ == "__main__": unittest.main()
