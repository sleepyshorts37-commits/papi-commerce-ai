import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from papi_core.anchor import AnchorClient, AnchorConflict, anchor_audit_journal
from papi_core.audit import append_event, new_event, read_events
from papi_core.audit_archive import (
    AuditArchiveError,
    create_verified_archive,
    restore_verified_archive,
    verify_archive,
    inspect_archive_recovery,
)


class MemoryAnchorStore:
    """Adaptateur mémoire de test uniquement."""

    def __init__(self):
        self.head = None
        self.objects = {}

    def get_head(self):
        return self.head

    def get_checkpoint(self, checkpoint_id):
        return self.objects.get(checkpoint_id)

    def put_checkpoint(self, checkpoint_id, payload):
        existing = self.objects.get(checkpoint_id)
        if existing is not None and existing != payload:
            raise AnchorConflict("immutable checkpoint collision")
        self.objects[checkpoint_id] = payload

    def compare_and_swap_head(self, expected, replacement):
        if self.head != expected:
            return False
        self.head = replacement
        return True


class AuditArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.journal = self.root / "events.jsonl"
        self.store = MemoryAnchorStore()
        self.client = AnchorClient(self.store)
        self._append("event-1", "job.created")
        self.checkpoint = anchor_audit_journal(
            self.client, self.journal, checkpoint_id="audit-checkpoint-1"
        )
        self.archive = self.root / "archive-001"

    def tearDown(self):
        self.temporary.cleanup()

    def _append(self, event_id, action):
        append_event(
            new_event(
                event_id=event_id,
                actor="system:test",
                action=action,
                entity_type="job",
                entity_id="job-archive-test",
                details={"result": "ok"},
            ),
            self.journal,
        )

    def _create(self):
        return create_verified_archive(self.journal, self.archive, self.client)

    def test_archive_is_verified_private_and_does_not_modify_source(self):
        original = self.journal.read_bytes()
        result = self._create()

        self.assertTrue(result["verified"])
        self.assertEqual(result["event_count"], 1)
        self.assertEqual(result["checkpoint_id"], self.checkpoint["checkpoint_id"])
        self.assertEqual(self.journal.read_bytes(), original)
        self.assertEqual(set(os.listdir(self.archive)), {"manifest.json", "journal.jsonl"})
        self.assertEqual(self.archive.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.archive / "manifest.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.archive / "journal.jsonl").stat().st_mode & 0o777, 0o600)

    def test_archive_creation_syncs_archive_and_parent_directories(self):
        from papi_core import audit_archive

        with patch(
            "papi_core.audit_archive._fsync_directory",
            wraps=audit_archive._fsync_directory,
        ) as sync_directory:
            self._create()

        self.assertEqual(
            [call.args[0] for call in sync_directory.call_args_list],
            [self.archive, self.root],
        )

    def test_restore_syncs_parent_directory_before_success(self):
        from papi_core import audit_archive

        self._create()
        restored_path = self.root / "durable-restored.jsonl"
        with patch(
            "papi_core.audit_archive._fsync_directory",
            wraps=audit_archive._fsync_directory,
        ) as sync_directory:
            result = restore_verified_archive(self.archive, restored_path, self.client)

        self.assertTrue(result["restored"])
        sync_directory.assert_called_once_with(self.root)

    def test_restore_fails_closed_when_parent_directory_sync_fails(self):
        self._create()
        restored_path = self.root / "not-durable.jsonl"
        with patch(
            "papi_core.audit_archive._fsync_directory",
            side_effect=AuditArchiveError("directory fsync unavailable"),
        ):
            with self.assertRaisesRegex(AuditArchiveError, "directory fsync unavailable"):
                restore_verified_archive(self.archive, restored_path, self.client)

        self.assertFalse(restored_path.exists())

    def test_restore_does_not_publish_a_partial_file_after_interrupted_write(self):
        self._create()
        restored_path = self.root / "interrupted.jsonl"
        real_write = os.write
        calls = 0

        def partial_then_fail(descriptor, payload):
            nonlocal calls
            calls += 1
            if calls == 1:
                # Archive verification writes its own private temporary copy first.
                return real_write(descriptor, payload)
            if calls == 2:
                return real_write(descriptor, payload[: max(1, len(payload) // 2)])
            raise OSError("simulated interrupted write")

        with patch("papi_core.audit_archive.os.write", side_effect=partial_then_fail):
            with self.assertRaisesRegex(AuditArchiveError, "Écriture temporaire"):
                restore_verified_archive(self.archive, restored_path, self.client)

        self.assertFalse(restored_path.exists())
        self.assertFalse(Path(f"{restored_path}.lock").exists())
        self.assertEqual(list(self.root.glob(f".{restored_path.name}.*.tmp")), [])

    def test_restore_does_not_publish_when_temporary_close_fails(self):
        self._create()
        restored_path = self.root / "close-failed.jsonl"
        real_mkstemp = tempfile.mkstemp
        real_close = os.close
        target_descriptors = set()
        mkstemp_calls = 0
        failed = False

        def track_mkstemp(*args, **kwargs):
            nonlocal mkstemp_calls
            descriptor, name = real_mkstemp(*args, **kwargs)
            mkstemp_calls += 1
            if mkstemp_calls == 2:
                target_descriptors.add(descriptor)
            return descriptor, name

        def close_then_fail(descriptor):
            nonlocal failed
            real_close(descriptor)
            if descriptor in target_descriptors and not failed:
                failed = True
                raise OSError("simulated close failure")

        with (
            patch("papi_core.audit_archive.tempfile.mkstemp", side_effect=track_mkstemp),
            patch("papi_core.audit_archive.os.close", side_effect=close_then_fail),
        ):
            with self.assertRaisesRegex(AuditArchiveError, "Fermeture"):
                restore_verified_archive(self.archive, restored_path, self.client)

        self.assertTrue(failed)
        self.assertFalse(restored_path.exists())
        self.assertFalse(Path(f"{restored_path}.lock").exists())
        self.assertEqual(list(self.root.glob(f".{restored_path.name}.*.tmp")), [])

    def test_archive_creation_removes_directory_when_temporary_close_fails(self):
        real_mkstemp = tempfile.mkstemp
        real_close = os.close
        target_descriptors = set()
        mkstemp_calls = 0
        failed = False

        def track_mkstemp(*args, **kwargs):
            nonlocal mkstemp_calls
            descriptor, name = real_mkstemp(*args, **kwargs)
            mkstemp_calls += 1
            if mkstemp_calls == 2:
                target_descriptors.add(descriptor)
            return descriptor, name

        def close_then_fail(descriptor):
            nonlocal failed
            real_close(descriptor)
            if descriptor in target_descriptors and not failed:
                failed = True
                raise OSError("simulated close failure")

        with (
            patch("papi_core.audit_archive.tempfile.mkstemp", side_effect=track_mkstemp),
            patch("papi_core.audit_archive.os.close", side_effect=close_then_fail),
        ):
            with self.assertRaisesRegex(AuditArchiveError, "Fermeture"):
                self._create()

        self.assertTrue(failed)
        self.assertFalse(self.archive.exists())
        self.assertEqual(list(self.root.glob(f".{self.archive.name}.*.tmp")), [])

    def test_archive_requires_a_checkpoint_matching_the_current_journal(self):
        self._append("event-2", "job.updated")
        with self.assertRaises(AuditArchiveError):
            self._create()
        self.assertFalse(self.archive.exists())

    def test_archive_requires_an_existing_verified_anchor(self):
        unanchored = AnchorClient(MemoryAnchorStore())
        with self.assertRaises(AuditArchiveError):
            create_verified_archive(self.journal, self.archive, unanchored)
        self.assertFalse(self.archive.exists())

    def test_archive_refuses_to_overwrite_an_existing_directory(self):
        self._create()
        before = (self.archive / "journal.jsonl").read_bytes()
        with self.assertRaises(AuditArchiveError):
            self._create()
        self.assertEqual((self.archive / "journal.jsonl").read_bytes(), before)

    def test_verification_rejects_modified_journal_bytes(self):
        self._create()
        path = self.archive / "journal.jsonl"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaises(AuditArchiveError):
            verify_archive(self.archive, self.client)

    def test_verification_rejects_duplicate_manifest_keys(self):
        self._create()
        path = self.archive / "manifest.json"
        original = path.read_bytes()
        path.write_bytes(original[:-1] + b',"version":1}')
        with self.assertRaises(AuditArchiveError):
            verify_archive(self.archive, self.client)

    def test_verification_rejects_symlinked_archive_files(self):
        self._create()
        archived_journal = self.archive / "journal.jsonl"
        archived_journal.unlink()
        os.symlink(self.journal, archived_journal)
        with self.assertRaises(AuditArchiveError):
            verify_archive(self.archive, self.client)

    def test_restore_recreates_verified_private_journal(self):
        self._create()
        restored_path = self.root / "restored.jsonl"

        result = restore_verified_archive(self.archive, restored_path, self.client)

        self.assertTrue(result["restored"])
        self.assertEqual(read_events(restored_path), read_events(self.journal))
        self.assertEqual(restored_path.read_bytes(), (self.archive / "journal.jsonl").read_bytes())
        self.assertEqual(restored_path.stat().st_mode & 0o777, 0o600)

    def test_restore_never_deletes_or_overwrites_an_existing_target(self):
        self._create()
        target = self.root / "existing.jsonl"
        target.write_bytes(b"keep this file")

        with self.assertRaises(FileExistsError):
            restore_verified_archive(self.archive, target, self.client)

        self.assertEqual(target.read_bytes(), b"keep this file")

    def test_older_archive_remains_verifiable_after_a_new_checkpoint(self):
        self._create()
        self._append("event-2", "job.updated")
        anchor_audit_journal(
            self.client, self.journal, checkpoint_id="audit-checkpoint-2"
        )

        result = verify_archive(self.archive, self.client)

        self.assertTrue(result["verified"])
        self.assertEqual(result["checkpoint_id"], "audit-checkpoint-1")
        self.assertEqual(result["event_count"], 1)


    def test_inspect_archive_reports_complete_structure_without_claiming_verification(self):
        self._create()
        result = inspect_archive_recovery(self.archive, kind="archive-directory")
        self.assertEqual(result["status"], "structurally_complete_unverified")
        self.assertFalse(result["cryptographic_verification_performed"])
        self.assertFalse(result["automatic_recovery"])
        self.assertEqual(
            {entry["name"] for entry in result["entries"]},
            {"manifest.json", "journal.jsonl"},
        )

    def test_inspect_archive_finds_orphan_temporary_without_mutating_it(self):
        self._create()
        temporary = self.archive / ".journal.jsonl.orphan.tmp"
        temporary.write_bytes(b"partial archive")
        temporary.chmod(0o600)
        original = temporary.read_bytes()
        result = inspect_archive_recovery(self.archive, kind="archive-directory")
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(
            [item["name"] for item in result["temporary_candidates"]],
            [temporary.name],
        )
        self.assertTrue(result["temporary_candidates"][0]["safe_to_inspect"])
        self.assertEqual(temporary.read_bytes(), original)
        self.assertTrue(temporary.exists())

    def test_inspect_restore_target_reports_candidate_without_promoting_or_deleting(self):
        target = self.root / "recovered.jsonl"
        temporary = self.root / ".recovered.jsonl.orphan.tmp"
        temporary.write_bytes(b"partial journal")
        temporary.chmod(0o600)
        original = temporary.read_bytes()
        result = inspect_archive_recovery(target, kind="restore-target")
        self.assertEqual(result["status"], "temporary_candidates_review_required")
        self.assertEqual(result["target_state"], "absent")
        self.assertEqual(
            [item["name"] for item in result["temporary_candidates"]],
            [temporary.name],
        )
        self.assertFalse(result["automatic_recovery"])
        self.assertFalse(target.exists())
        self.assertEqual(temporary.read_bytes(), original)

    def test_inspect_restore_target_flags_symlink_candidate_as_unsafe(self):
        target = self.root / "linked.jsonl"
        temporary = self.root / ".linked.jsonl.fake.tmp"
        try:
            os.symlink(self.journal, temporary)
        except (OSError, NotImplementedError):
            self.skipTest("Liens symboliques indisponibles sur cette plateforme.")
        result = inspect_archive_recovery(target, kind="restore-target")
        self.assertEqual(result["status"], "temporary_candidates_review_required")
        self.assertEqual(result["temporary_candidates"][0]["kind"], "symlink")
        self.assertFalse(result["temporary_candidates"][0]["safe_to_inspect"])
        self.assertTrue(temporary.is_symlink())

    def test_inspect_restore_target_flags_overly_permissive_temporary(self):
        target = self.root / "private.jsonl"
        temporary = self.root / ".private.jsonl.orphan.tmp"
        temporary.write_bytes(b"partial journal")
        temporary.chmod(0o644)
        result = inspect_archive_recovery(target, kind="restore-target")
        self.assertFalse(result["temporary_candidates"][0]["safe_to_inspect"])
        self.assertFalse(result["automatic_recovery"])


    def test_inspection_pins_parent_before_ancestor_is_replaced(self):
        base = self.root / "base"
        alias = base / "alias"
        parent = alias / "parent"
        archive = parent / "archive"
        archive.mkdir(parents=True, mode=0o700)
        archive.chmod(0o700)
        for name, payload in (
            ("manifest.json", b"{}"),
            ("journal.jsonl", b"{}\\n"),
        ):
            item = archive / name
            item.write_bytes(payload)
            item.chmod(0o600)

        attacker = self.root / "attacker"
        (attacker / "parent" / "archive").mkdir(parents=True, mode=0o700)
        (attacker / "parent" / "archive").chmod(0o700)
        moved_alias = base / "alias-original"
        original_open = os.open
        swapped = False

        def replace_ancestor_before_descending(path, flags, *args, **kwargs):
            nonlocal swapped
            if not swapped and Path(path).name == "parent":
                os.rename(alias, moved_alias)
                os.symlink(attacker, alias)
                swapped = True
            return original_open(path, flags, *args, **kwargs)

        with patch(
            "papi_core.audit_archive.os.open",
            side_effect=replace_ancestor_before_descending,
        ):
            result = inspect_archive_recovery(archive, kind="archive-directory")

        self.assertTrue(swapped)
        self.assertEqual(result["status"], "structurally_complete_unverified")
        self.assertEqual(
            {entry["name"] for entry in result["entries"]},
            {"manifest.json", "journal.jsonl"},
        )
        self.assertTrue(alias.is_symlink())

if __name__ == "__main__":
    unittest.main()
