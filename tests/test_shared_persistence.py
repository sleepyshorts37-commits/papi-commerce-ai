import unittest
from unittest.mock import Mock

from papi_core.principal import _issue_authenticated_agent_principal
from papi_core.shared_persistence import (
    SharedChatAdapter, SharedMemoryAdapter, SharedPersistenceError,
)
from papi_core.storage import SupabaseStore


class SharedPersistenceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.store = SupabaseStore(url="https://example.supabase.co", key="test-key")
        self.store.request = Mock()
        self.memory = SharedMemoryAdapter(self.store)
        self.chat = SharedChatAdapter(self.store)
        self.astou = _issue_authenticated_agent_principal("astou")

    def test_memory_append_maps_source_to_columns(self):
        self.store.request.return_value = [{"event_id": "e1"}]
        self.memory.append_event({
            "event_id": "e1", "event_type": "remember", "memory_id": "m1",
            "created_at": "2026-01-01T00:00:00Z", "actor": "astou",
            "category": "fact", "title": "Fact", "content": "Text",
            "source": {"type": "task", "id": "T-1"}, "confidence": 0.9,
            "scope": "shared", "tags": ["papi"], "sensitivity": "normal",
        })
        args = self.store.request.call_args.args
        self.assertEqual(args[0:2], ("POST", "papi_memory_events"))
        self.assertEqual(args[2]["source_type"], "task")
        self.assertEqual(args[2]["source_id"], "T-1")

    def test_memory_search_requires_authenticated_principal(self):
        with self.assertRaises(PermissionError):
            self.memory.search(principal="astou")

    def test_memory_search_filters_by_actor_and_reverses_superseded(self):
        rows = [
            {"event_type": "remember", "memory_id": "m1", "event_id": "e1",
             "created_at": "2026-01-01", "actor": "astou", "category": "fact",
             "title": "Old", "content": "old fact", "source_type": "task",
             "source_id": "T1", "confidence": 0.8, "scope": "shared",
             "tags": [], "sensitivity": "normal"},
            {"event_type": "supersede", "memory_id": "m1", "target_memory_id": "m1",
             "event_id": "e2", "created_at": "2026-01-02", "actor": "astou"},
            {"event_type": "remember", "memory_id": "m2", "event_id": "e3",
             "created_at": "2026-01-03", "actor": "astou", "category": "fact",
             "title": "Current", "content": "current fact", "source_type": "task",
             "source_id": "T2", "confidence": 0.9, "scope": "shared",
             "tags": ["papi"], "sensitivity": "normal"},
        ]
        self.store.request.return_value = rows
        result = self.memory.search(principal=self.astou, query="current")
        self.assertEqual([item["memory_id"] for item in result], ["m2"])
        query = self.store.request.call_args.args[1]
        self.assertIn("scope.eq.agent,actor.eq.astou", query)
        self.assertIn("event_type.eq.supersede", query)

    def test_chat_read_is_scoped_and_ordered(self):
        self.store.request.return_value = [
            {"message_id": "MSG-B", "recipient": "astou"},
            {"message_id": "MSG-A", "recipient": "all"},
        ]
        result = self.chat.read_messages(principal=self.astou, limit=10)
        self.assertEqual([item["message_id"] for item in result], ["MSG-A", "MSG-B"])
        query = self.store.request.call_args.args[1]
        self.assertIn("recipient.eq.astou", query)
        self.assertIn("recipient.eq.all", query)

    def test_chat_read_rejects_raw_identity(self):
        with self.assertRaises(PermissionError):
            self.chat.read_messages(principal="astou")

    def test_append_requires_confirmed_insert(self):
        self.store.request.return_value = []
        with self.assertRaises(Exception):
            self.chat.append_message({
                "message_id": "MSG-" + "A" * 32, "sent_at": "2026-01-01T00:00:00Z",
                "sender": "astou", "recipient": "all", "subject": "Hi",
                "body": "Hello", "message_type": "info",
            })


if __name__ == "__main__":
    unittest.main()
