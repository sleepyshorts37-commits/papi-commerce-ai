import hashlib
import unittest

from papi_core.backup_restore import (
    BackupValidationError, build_restore_plan, validate_backup_manifest,
)


class BackupRestoreTests(unittest.TestCase):
    def setUp(self):
        self.payloads = {"database/schema.sql": b"CREATE TABLE example (id int);"}
        content = self.payloads["database/schema.sql"]
        self.manifest = {
            "backup_id": "backup-test-001",
            "created_at": "2026-11-13T12:00:00Z",
            "source": "isolated-test-fixture",
            "schema_version": "test-schema-v1",
            "retention_days": 30,
            "artifacts": [{
                "path": "database/schema.sql",
                "sha256": hashlib.sha256(content).hexdigest(),
                "size_bytes": len(content),
                "kind": "sql_schema",
            }],
        }

    def test_valid_manifest_verifies_without_restore(self):
        result = validate_backup_manifest(self.manifest, self.payloads)
        self.assertEqual(result["status"], "verified")
        self.assertFalse(result["restore_performed"])
        self.assertFalse(result["remote_storage_accessed"])

    def test_restore_plan_requires_review_and_performs_no_write(self):
        plan = build_restore_plan(self.manifest, self.payloads, target_environment="isolated")
        self.assertEqual(plan["status"], "ready_for_human_review")
        self.assertTrue(plan["human_approval_required"])
        self.assertFalse(plan["writes_performed"])
        self.assertFalse(plan["restore_performed"])

    def test_tampered_payload_is_rejected(self):
        with self.assertRaises(BackupValidationError):
            validate_backup_manifest(self.manifest, {"database/schema.sql": b"tampered"})

    def test_missing_payload_is_rejected(self):
        with self.assertRaises(BackupValidationError):
            validate_backup_manifest(self.manifest, {})

    def test_unlisted_payload_is_rejected(self):
        with self.assertRaises(BackupValidationError):
            validate_backup_manifest(self.manifest, {
                **self.payloads, "extra.bin": b"unexpected"
            })

    def test_path_traversal_is_rejected(self):
        bad = {**self.manifest, "artifacts": [
            {**self.manifest["artifacts"][0], "path": "../secrets.env"}
        ]}
        with self.assertRaises(BackupValidationError):
            validate_backup_manifest(bad, {"../secrets.env": self.payloads["database/schema.sql"]})

    def test_absolute_path_is_rejected(self):
        bad = {**self.manifest, "artifacts": [
            {**self.manifest["artifacts"][0], "path": "/tmp/backup.sql"}
        ]}
        with self.assertRaises(BackupValidationError):
            validate_backup_manifest(bad, {"/tmp/backup.sql": self.payloads["database/schema.sql"]})

    def test_non_utc_timestamp_is_rejected(self):
        bad = {**self.manifest, "created_at": "2026-11-13T13:00:00+01:00"}
        with self.assertRaises(BackupValidationError):
            validate_backup_manifest(bad, self.payloads)

    def test_invalid_retention_is_rejected(self):
        for value in (0, -1, 3651, True):
            with self.subTest(value=value):
                bad = {**self.manifest, "retention_days": value}
                with self.assertRaises(BackupValidationError):
                    validate_backup_manifest(bad, self.payloads)

    def test_duplicate_artifact_path_is_rejected(self):
        bad = {**self.manifest, "artifacts": [
            *self.manifest["artifacts"], self.manifest["artifacts"][0]
        ]}
        with self.assertRaises(BackupValidationError):
            validate_backup_manifest(bad, self.payloads)

    def test_empty_restore_target_is_rejected(self):
        with self.assertRaises(BackupValidationError):
            build_restore_plan(self.manifest, self.payloads, target_environment=" ")


if __name__ == "__main__":
    unittest.main()
