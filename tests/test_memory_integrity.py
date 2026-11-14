import json
import tempfile
import unittest
from pathlib import Path

from papi_core.memory import MemoryError, _read_events


class MemoryJournalIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "events.jsonl"

    def tearDown(self):
        self.temp.cleanup()

    def write(self, *events):
        self.path.write_text("".join(json.dumps(event) + "\\n" for event in events), encoding="utf-8")

    def remember(self, **changes):
        event = {
            "event_id": "event-1", "event_type": "remember", "memory_id": "memory-1",
            "created_at": "2026-11-14T10:00:00Z", "actor": "astou", "category": "fact",
            "title": "Projet", "content": "Mémoire testée", "source": {"type": "task", "id": "TASK-1"},
            "confidence": 0.8, "scope": "shared", "tags": [], "sensitivity": "normal",
        }
        event.update(changes)
        return event

    def test_valid_remember_event_is_read(self):
        event = self.remember()
        self.write(event)
        self.assertEqual(_read_events(self.path), [event])

    def test_missing_required_field_is_rejected(self):
        event = self.remember()
        del event["source"]
        self.write(event)
        with self.assertRaises(MemoryError):
            _read_events(self.path)

    def test_invalid_timestamp_without_timezone_is_rejected(self):
        self.write(self.remember(created_at="2026-11-14T10:00:00"))
        with self.assertRaises(MemoryError):
            _read_events(self.path)

    def test_non_finite_confidence_is_rejected(self):
        self.write(self.remember(confidence=float("nan")))
        with self.assertRaises(MemoryError):
            _read_events(self.path)

    def test_sensitive_nested_source_field_is_rejected(self):
        self.write(self.remember(source={"type": "task", "id": "TASK-1", "email": "private@example.com"}))
        with self.assertRaises(MemoryError):
            _read_events(self.path)

    def test_duplicate_memory_ids_are_rejected(self):
        self.write(self.remember(), self.remember(event_id="event-2"))
        with self.assertRaises(MemoryError):
            _read_events(self.path)

    def test_orphan_supersede_is_rejected(self):
        event = {"event_id": "event-2", "event_type": "supersede",
                 "created_at": "2026-11-14T10:00:00Z", "actor": "astou",
                 "target_memory_id": "missing", "reason": "Correction"}
        self.write(event)
        with self.assertRaises(MemoryError):
            _read_events(self.path)

    def test_duplicate_supersede_is_rejected(self):
        first = self.remember()
        archive = {"event_id": "event-2", "event_type": "supersede",
                   "created_at": "2026-11-14T10:01:00Z", "actor": "astou",
                   "target_memory_id": "memory-1", "reason": "Correction"}
        second = dict(archive, event_id="event-3")
        self.write(first, archive, second)
        with self.assertRaises(MemoryError):
            _read_events(self.path)


if __name__ == "__main__":
    unittest.main()
