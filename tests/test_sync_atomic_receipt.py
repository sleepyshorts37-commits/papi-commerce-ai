import hashlib, sqlite3, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from papi_core.identity_ed25519 import provision_ed25519_agent
from papi_core.sync_bundle import build_sync_bundle
from papi_core.sync_bundle_approval import sign_sync_bundle_approval
from papi_core.sync_atomic_receipt import AtomicSyncReceiptError, commit_approved_sync_receipt

NOW=datetime(2026,11,14,12,0,tzinfo=timezone.utc)
A=hashlib.sha256(b"atomic-a").hexdigest()
B=hashlib.sha256(b"atomic-b").hexdigest()

class AtomicSyncReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.registry=self.root/"public.json"
        self.db=self.root/"atomic-ledger.sqlite3"
        self.private=provision_ed25519_agent("owner-42",self.root/"keys",self.registry)
    def tearDown(self): self.temp.cleanup()
    def bundle(self,export="export-42",events=None):
        events=events or [{"event_id":"evt-42-a","kind":"memory","record_id":"MEM-42-A","sequence":1,"content_digest":A}]
        return build_sync_bundle(source_instance_id="instance-a",destination_instance_id="instance-b",
            export_id=export,created_at="2026-11-14T11:59:00Z",
            cursor_start=1,cursor_end=len(events),events=events)
    def signed(self,bundle,approval="APR-42",nonce="nonce-atomic-42-0001"):
        return sign_sync_bundle_approval(owner_id="owner-42",private_key_path=self.private,bundle=bundle,
            approval_id=approval,issued_at="2026-11-14T12:00:00Z",
            expires_at="2026-11-14T12:10:00Z",nonce=nonce,timestamp=int(NOW.timestamp()))
    def commit(self,bundle,envelope):
        return commit_approved_sync_receipt(envelope=envelope,bundle=bundle,owner_id="owner-42",
            registry_path=self.registry,ledger_db=self.db,expected_destination="instance-b",
            now_epoch=int(NOW.timestamp()),now=NOW)
    def counts(self):
        with sqlite3.connect(self.db) as db:
            return (db.execute("SELECT COUNT(*) FROM used_nonces").fetchone()[0],
                    db.execute("SELECT COUNT(*) FROM sync_bundle_receipts").fetchone()[0],
                    db.execute("SELECT COUNT(*) FROM sync_bundle_receipt_items").fetchone()[0])
    def test_nonce_and_receipt_commit_together(self):
        bundle=self.bundle()
        result=self.commit(bundle,self.signed(bundle))
        self.assertTrue(result["nonce_consumed_atomically"])
        self.assertTrue(result["receipt_committed"])
        self.assertEqual(self.counts(),(1,1,1))
    def test_replay_rejected(self):
        bundle=self.bundle(); envelope=self.signed(bundle)
        self.commit(bundle,envelope)
        with self.assertRaises(AtomicSyncReceiptError): self.commit(bundle,envelope)
        self.assertEqual(self.counts(),(1,1,1))
    def test_same_bundle_new_approval_is_idempotent_and_consumes_new_nonce(self):
        bundle=self.bundle(); self.commit(bundle,self.signed(bundle))
        result=self.commit(bundle,self.signed(bundle,"APR-42-RETRY","nonce-atomic-42-0002"))
        self.assertEqual(result["status"],"already_recorded")
        self.assertEqual(self.counts(),(2,1,1))
    def test_conflicting_event_rolls_back_nonce_and_partial_receipt(self):
        first=self.bundle(); self.commit(first,self.signed(first))
        conflict=self.bundle("export-42-b",[
            {"event_id":"evt-42-b","kind":"memory","record_id":"MEM-42-B","sequence":1,"content_digest":B},
            {"event_id":"evt-42-a","kind":"memory","record_id":"MEM-42-C","sequence":2,"content_digest":B}])
        envelope=self.signed(conflict,"APR-42-CONFLICT","nonce-atomic-42-0003")
        before=self.counts()
        with self.assertRaises(AtomicSyncReceiptError): self.commit(conflict,envelope)
        self.assertEqual(self.counts(),before)
    def test_conflicting_resource_rolls_back_nonce(self):
        first=self.bundle(); self.commit(first,self.signed(first))
        conflict=self.bundle("export-42-c",[{"event_id":"evt-42-c","kind":"memory",
            "record_id":"MEM-42-A","sequence":1,"content_digest":B}])
        before=self.counts()
        with self.assertRaises(AtomicSyncReceiptError):
            self.commit(conflict,self.signed(conflict,"APR-42-C","nonce-atomic-42-0004"))
        self.assertEqual(self.counts(),before)
    def test_wrong_destination_does_not_consume_nonce(self):
        bundle=self.bundle(); envelope=self.signed(bundle)
        with self.assertRaises(AtomicSyncReceiptError):
            commit_approved_sync_receipt(envelope=envelope,bundle=bundle,owner_id="owner-42",
                registry_path=self.registry,ledger_db=self.db,expected_destination="instance-c",
                now_epoch=int(NOW.timestamp()),now=NOW)
        self.assertFalse(self.db.exists())

if __name__=="__main__": unittest.main()
