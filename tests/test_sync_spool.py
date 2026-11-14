import hashlib, tempfile, unittest
from pathlib import Path
from papi_core.identity_ed25519 import provision_ed25519_agent
from papi_core.sync_bundle import build_sync_bundle
from papi_core.sync_bundle_approval import sign_sync_bundle_approval
from papi_core.sync_spool import SyncSpoolError, read_sync_package, write_sync_package
NOW=1794657600
DIGEST=hashlib.sha256(b"sync-spool-event").hexdigest()
class SyncSpoolTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.registry=self.root/"public.json"; self.private=provision_ed25519_agent("owner-43",self.root/"keys",self.registry)
        self.spool=self.root/"spool"
        self.bundle=build_sync_bundle(source_instance_id="instance-a",destination_instance_id="instance-b",export_id="export-43",
            created_at="2026-11-14T12:00:00Z",cursor_start=1,cursor_end=1,
            events=[{"event_id":"evt-43-a","kind":"memory","record_id":"MEM-43-A","sequence":1,"content_digest":DIGEST}])
        self.approval=sign_sync_bundle_approval(owner_id="owner-43",private_key_path=self.private,bundle=self.bundle,
            approval_id="APR-43",issued_at="2026-11-14T12:00:00Z",expires_at="2026-11-14T12:10:00Z",
            nonce="nonce-spool-43-0001",timestamp=NOW)
    def tearDown(self): self.temp.cleanup()
    def test_write_and_read_round_trip(self):
        result=write_sync_package(bundle=self.bundle,approval=self.approval,spool_dir=self.spool)
        loaded=read_sync_package(Path(result["path"]))
        self.assertEqual(loaded["bundle"],self.bundle); self.assertEqual(loaded["approval"],self.approval)
        self.assertFalse(loaded["signature_verified"]); self.assertFalse(loaded["nonce_consumed"])
        self.assertEqual(Path(result["path"]).stat().st_mode&0o777,0o600); self.assertEqual(self.spool.stat().st_mode&0o777,0o700)
    def test_duplicate_write_never_overwrites(self):
        first=write_sync_package(bundle=self.bundle,approval=self.approval,spool_dir=self.spool); original=Path(first["path"]).read_bytes()
        with self.assertRaises(SyncSpoolError): write_sync_package(bundle=self.bundle,approval=self.approval,spool_dir=self.spool)
        self.assertEqual(Path(first["path"]).read_bytes(),original)
    def test_modified_bytes_rejected(self):
        result=write_sync_package(bundle=self.bundle,approval=self.approval,spool_dir=self.spool); path=Path(result["path"])
        path.write_bytes(path.read_bytes()+b" ")
        with self.assertRaises(SyncSpoolError): read_sync_package(path)
    def test_approval_for_other_bundle_rejected(self):
        changed=dict(self.bundle); changed["export_id"]="different-export"
        with self.assertRaises(SyncSpoolError): write_sync_package(bundle=changed,approval=self.approval,spool_dir=self.spool)
    def test_symlink_rejected(self):
        result=write_sync_package(bundle=self.bundle,approval=self.approval,spool_dir=self.spool); target=Path(result["path"])
        link=self.spool/("f"*64+".papisync"); link.symlink_to(target)
        with self.assertRaises(SyncSpoolError): read_sync_package(link)
    def test_duplicate_json_keys_rejected(self):
        result=write_sync_package(bundle=self.bundle,approval=self.approval,spool_dir=self.spool); path=Path(result["path"])
        path.write_text('{"format_version":1,"format_version":1}',encoding="utf-8")
        with self.assertRaises(SyncSpoolError): read_sync_package(path)
    def test_wrong_filename_rejected(self):
        result=write_sync_package(bundle=self.bundle,approval=self.approval,spool_dir=self.spool); path=Path(result["path"])
        wrong=path.with_name("unsafe-name.papisync"); path.rename(wrong)
        with self.assertRaises(SyncSpoolError): read_sync_package(wrong)
if __name__=="__main__": unittest.main()
