import unittest
from datetime import datetime, timezone, timedelta

from papi_core.papi_kids_backup_ops import (
    PapiKidsBackupOpsError,
    evaluate_backup_health,
    load_backup_health_inventory,
    plan_backup_retention,
)


class PapiKidsBackupOpsTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)

    def backup(self, name, created):
        return {
            "backup_file": name,
            "created_at": created.isoformat(),
            "encrypted_sha256": f"{len(name):064x}",
            "offsite_copy_verified": True,
            "offsite_evidence_ref": "storage-proof-01",
        }

    def test_retention_plan_keeps_daily_weekly_monthly_and_never_deletes(self):
        backups = [
            self.backup(f"backup-{i}", self.now - timedelta(days=i))
            for i in range(0, 40)
        ]
        result = plan_backup_retention(backups, now=self.now)
        retained_names = {item["backup_file"] for item in result["retained"]}
        self.assertIn("backup-0", retained_names)
        self.assertGreater(len(result["retained"]), 7)
        self.assertGreater(len(result["deletion_candidates"]), 0)
        self.assertFalse(result["deletion_performed"])
        self.assertTrue(result["human_approval_required_before_deletion"])

    def test_rejects_duplicate_names_bad_hash_and_naive_time(self):
        with self.assertRaises(PapiKidsBackupOpsError):
            plan_backup_retention([self.backup("same", self.now), self.backup("same", self.now)], now=self.now)
        bad = self.backup("bad", self.now)
        bad["encrypted_sha256"] = "not-a-hash"
        with self.assertRaises(PapiKidsBackupOpsError):
            plan_backup_retention([bad], now=self.now)
        naive = self.backup("naive", self.now)
        naive["created_at"] = "2026-11-15T12:00:00"
        with self.assertRaises(PapiKidsBackupOpsError):
            plan_backup_retention([naive], now=self.now)

    def test_backup_health_requires_fresh_backup_offsite_and_recent_restore(self):
        backups = [self.backup("latest", self.now - timedelta(hours=2))]
        result = evaluate_backup_health(
            backups, last_restore_drill_at=(self.now - timedelta(days=4)).isoformat(),
            now=self.now,
        )
        self.assertEqual(result["status"], "healthy")
        self.assertTrue(result["backup_fresh"])
        self.assertTrue(result["offsite_verified"])
        self.assertTrue(result["restore_drill_fresh"])

    def test_missing_offsite_or_old_restore_drill_is_unhealthy(self):
        backup = self.backup("latest", self.now - timedelta(hours=2))
        backup["offsite_copy_verified"] = False
        result = evaluate_backup_health(
            [backup], last_restore_drill_at=(self.now - timedelta(days=60)).isoformat(),
            now=self.now,
        )
        self.assertEqual(result["status"], "unhealthy")
        self.assertEqual(len(result["blockers"]), 2)

    def test_health_inventory_uses_only_matching_offsite_proof(self):
        import hashlib
        import json
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as root:
            backup = Path(root) / "backup-01.pgdump.aesgcm"
            backup.write_bytes(b"encrypted archive")
            digest = hashlib.sha256(backup.read_bytes()).hexdigest()
            manifest = {
                "backup_file": backup.name, "encrypted": True,
                "encrypted_sha256": digest, "created_at": self.now.isoformat(),
            }
            Path(str(backup) + ".json").write_text(json.dumps(manifest))
            verified_at = self.now.isoformat()
            remote = "drive:papi-kids-backups"
            evidence = hashlib.sha256(
                f"{backup.name}:{digest}:{remote}:{datetime.fromisoformat(verified_at)}".encode("utf-8")
            ).hexdigest()
            proof = {
                "status": "offsite_copy_verified", "checksum_verified": True,
                "verified_at": verified_at, "remote": remote,
                "backups": [{
                    "backup_file": backup.name, "encrypted_sha256": digest,
                    "offsite_copy_verified": True, "offsite_evidence_ref": evidence,
                }],
            }
            (Path(root) / "offsite-verification.json").write_text(json.dumps(proof))
            inventory = load_backup_health_inventory(root)
            self.assertTrue(inventory[0]["offsite_copy_verified"])
            self.assertEqual(inventory[0]["offsite_evidence_ref"], evidence)

    def test_tampered_offsite_evidence_does_not_mark_backup_verified(self):
        import hashlib
        import json
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as root:
            backup = Path(root) / "backup-02.pgdump.aesgcm"
            backup.write_bytes(b"encrypted archive")
            digest = hashlib.sha256(backup.read_bytes()).hexdigest()
            manifest = {
                "backup_file": backup.name, "encrypted": True,
                "encrypted_sha256": digest, "created_at": self.now.isoformat(),
            }
            Path(str(backup) + ".json").write_text(json.dumps(manifest))
            verified_at = self.now.isoformat()
            remote = "drive:papi-kids-backups"
            proof = {
                "status": "offsite_copy_verified", "checksum_verified": True,
                "verified_at": verified_at, "remote": remote,
                "backups": [{
                    "backup_file": backup.name, "encrypted_sha256": "0" * 64,
                    "offsite_copy_verified": True, "offsite_evidence_ref": "0" * 64,
                }],
            }
            (Path(root) / "offsite-verification.json").write_text(json.dumps(proof))
            inventory = load_backup_health_inventory(root)
            self.assertFalse(inventory[0]["offsite_copy_verified"])

    def test_empty_inventory_is_unhealthy(self):
        result = evaluate_backup_health([], last_restore_drill_at=None, now=self.now)
        self.assertEqual(result["status"], "unhealthy")
        self.assertEqual(len(result["blockers"]), 1)


if __name__ == "__main__":
    unittest.main()
