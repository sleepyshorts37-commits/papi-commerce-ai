import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from papi_core.memory import MemoryError, remember_fact, search_memory, supersede_memory
from papi_core.principal import _issue_authenticated_agent_principal


class SharedMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "memory.jsonl"
        self.astou = _issue_authenticated_agent_principal("astou")
        self.sokhna = _issue_authenticated_agent_principal("sokhna")

    def tearDown(self):
        self.temp.cleanup()

    def remember(self, **kwargs):
        defaults = dict(principal=self.astou, category="fact", title="Projet PAPI",
                        content="Le chat interne utilise un journal local.",
                        source_type="task", source_id="TASK-1", path=self.path)
        defaults.update(kwargs)
        return remember_fact(**defaults)

    def test_remember_and_search(self):
        saved = self.remember()
        found = search_memory(query="journal local", principal=self.astou, path=self.path)
        self.assertEqual(found[0]["memory_id"], saved["memory_id"])

    def test_agent_scope_is_private_to_author(self):
        self.remember(scope="agent")
        self.assertEqual(search_memory(principal=self.sokhna, path=self.path), [])
        self.assertEqual(len(search_memory(principal=self.astou, path=self.path)), 1)

    def test_agent_cannot_create_owner_scope(self):
        with self.assertRaises(MemoryError):
            self.remember(scope="owner")

    def test_agent_cannot_claim_owner_identity_for_decision(self):
        with self.assertRaises(MemoryError):
            self.remember(category="decision")

    def test_secret_like_content_is_rejected(self):
        with self.assertRaises(MemoryError):
            self.remember(content="Bearer abcdefghijklmnopqrstuvwxyz1234")

    def test_sensitive_fields_are_rejected(self):
        with self.assertRaises(MemoryError):
            self.remember(content={"email": "person@example.com"})

    def test_supersede_preserves_history_and_hides_old_entry(self):
        saved = self.remember()
        self.assertTrue(supersede_memory(memory_id=saved["memory_id"], principal=self.astou,
                                         reason="Information remplacée.", path=self.path))
        self.assertEqual(search_memory(principal=self.astou, path=self.path), [])
        self.assertFalse(supersede_memory(memory_id=saved["memory_id"], principal=self.astou,
                                          reason="Doublon.", path=self.path))
        self.assertEqual(len(self.path.read_text(encoding="utf-8").splitlines()), 2)

    def test_raw_actor_string_cannot_authenticate_memory_access(self):
        with self.assertRaises(PermissionError):
            search_memory(principal="owner", path=self.path)
        with self.assertRaises(PermissionError):
            remember_fact(principal="owner", category="fact", title="T",
                          content="C", source_type="task", source_id="T-1",
                          path=self.path)

    def test_agent_cannot_archive_another_agents_private_memory(self):
        saved = self.remember(principal=self.sokhna, scope="agent")
        with self.assertRaises(MemoryError):
            supersede_memory(memory_id=saved["memory_id"], principal=self.astou,
                             reason="Tentative.", path=self.path)


    def test_concurrent_appends_preserve_every_jsonl_record(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            saved = list(pool.map(
                lambda index: self.remember(title=f"Événement {index}"),
                range(32),
            ))
        events = search_memory(principal=self.astou, path=self.path, limit=100)
        self.assertEqual(len(events), 32)
        self.assertEqual({item["memory_id"] for item in events},
                         {item["memory_id"] for item in saved})

    def test_concurrent_supersede_archives_only_once(self):
        saved = self.remember()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(
                lambda _: supersede_memory(
                    memory_id=saved["memory_id"], principal=self.astou,
                    reason="Archivage concurrent.", path=self.path,
                ),
                range(8),
            ))
        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), 7)
        self.assertEqual(len(self.path.read_text(encoding="utf-8").splitlines()), 2)

    def test_fifo_journal_is_rejected_without_blocking(self):
        if not hasattr(os, "mkfifo"):
            self.skipTest("FIFO tests require POSIX mkfifo")

        os.mkfifo(self.path)
        with self.assertRaises(MemoryError):
            search_memory(principal=self.astou, path=self.path)

        write_path = self.path.parent / "write-pipe.jsonl"
        os.mkfifo(write_path)
        with self.assertRaises(MemoryError):
            self.remember(path=write_path)

    def test_memory_journal_symlink_is_rejected(self):
        target = self.path.parent / "target.jsonl"
        target.write_text("", encoding="utf-8")
        self.path.symlink_to(target)
        with self.assertRaises(MemoryError):
            self.remember()
        self.assertEqual(target.read_text(encoding="utf-8"), "")

    def test_invalid_limit_is_rejected(self):
        with self.assertRaises(MemoryError):
            search_memory(principal=self.astou, limit=0, path=self.path)


if __name__ == "__main__":
    unittest.main()
