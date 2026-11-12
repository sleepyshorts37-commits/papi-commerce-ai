import tempfile
import unittest
from pathlib import Path

from papi_core.memory import MemoryError, remember_fact, search_memory, supersede_memory


class SharedMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "memory.jsonl"

    def tearDown(self):
        self.temp.cleanup()

    def remember(self, **kwargs):
        defaults = dict(actor="astou", category="fact", title="Projet PAPI",
                        content="Le chat interne utilise un journal local.",
                        source_type="task", source_id="TASK-1", path=self.path)
        defaults.update(kwargs)
        return remember_fact(**defaults)

    def test_remember_and_search(self):
        saved = self.remember()
        found = search_memory(query="journal local", actor="owner", path=self.path)
        self.assertEqual(found[0]["memory_id"], saved["memory_id"])

    def test_agent_scope_is_private_to_author(self):
        self.remember(scope="agent")
        self.assertEqual(search_memory(actor="sokhna", path=self.path), [])
        self.assertEqual(len(search_memory(actor="astou", path=self.path)), 1)

    def test_owner_scope_is_private(self):
        self.remember(actor="owner", scope="owner")
        self.assertEqual(search_memory(actor="astou", path=self.path), [])
        self.assertEqual(len(search_memory(actor="owner", path=self.path)), 1)

    def test_only_owner_can_record_official_decision(self):
        with self.assertRaises(MemoryError):
            self.remember(category="decision")

    def test_owner_can_record_decision(self):
        saved = self.remember(actor="owner", category="decision")
        self.assertEqual(saved["category"], "decision")

    def test_secret_like_content_is_rejected(self):
        with self.assertRaises(MemoryError):
            self.remember(content="Bearer abcdefghijklmnopqrstuvwxyz1234")

    def test_sensitive_fields_are_rejected(self):
        with self.assertRaises(MemoryError):
            self.remember(content={"email": "person@example.com"})

    def test_supersede_preserves_history_and_hides_old_entry(self):
        saved = self.remember()
        self.assertTrue(supersede_memory(memory_id=saved["memory_id"], actor="astou",
                                         reason="Information remplacée.", path=self.path))
        self.assertEqual(search_memory(actor="owner", path=self.path), [])
        self.assertFalse(supersede_memory(memory_id=saved["memory_id"], actor="astou",
                                          reason="Doublon.", path=self.path))
        self.assertEqual(len(self.path.read_text(encoding="utf-8").splitlines()), 2)

    def test_non_owner_cannot_archive_official_decision(self):
        saved = self.remember(actor="owner", category="decision")
        with self.assertRaises(MemoryError):
            supersede_memory(memory_id=saved["memory_id"], actor="astou",
                             reason="Tentative.", path=self.path)


    def test_corrupted_event_schema_fails_closed(self):
        self.path.write_text('{"event_type":"remember","event_id":"x"}\n', encoding="utf-8")
        with self.assertRaises(MemoryError):
            search_memory(actor="owner", path=self.path)

    def test_invalid_event_metadata_fails_closed(self):
        saved = self.remember()
        lines = self.path.read_text(encoding="utf-8").splitlines()
        import json
        event = json.loads(lines[0])
        event["scope"] = "public"
        self.path.write_text(json.dumps(event) + "\n", encoding="utf-8")
        with self.assertRaises(MemoryError):
            search_memory(actor="owner", path=self.path)

    def test_invalid_limit_is_rejected(self):
        with self.assertRaises(MemoryError):
            search_memory(limit=0, path=self.path)


if __name__ == "__main__":
    unittest.main()
