import unittest
from unittest.mock import Mock

from papi_core.principal import _issue_authenticated_agent_principal
from papi_core.shared_persistence import (
    SharedChatAdapter, SharedMemoryAdapter, SharedPersistenceError,
)
from papi_core.storage import StoreError, SupabaseStore


class SharedPersistenceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.store = SupabaseStore(url="https://example.supabase.co", key="test-key")
        self.store.request = Mock()
        self.memory = SharedMemoryAdapter(self.store)
        self.chat = SharedChatAdapter(self.store)
        self.astou = _issue_authenticated_agent_principal("astou")
        self.sokhna = _issue_authenticated_agent_principal("sokhna")

    def valid_memory_event(self):
        return {
            "event_id": "11111111-1111-4111-8111-111111111111",
            "event_type": "remember",
            "memory_id": "22222222-2222-4222-8222-222222222222",
            "created_at": "2026-01-01T00:00:00Z", "actor": "astou",
            "category": "fact", "title": "Fact", "content": "Text",
            "source": {"type": "task", "id": "T-1"}, "confidence": 0.9,
            "scope": "shared", "tags": ["papi"], "sensitivity": "normal",
        }

    def valid_chat_message(self):
        return {
            "message_id": "MSG-" + "A" * 32, "sent_at": "2026-01-01T00:00:00Z",
            "sender": "astou", "recipient": "all", "subject": "Hi",
            "body": "Hello", "message_type": "info",
        }

    def test_memory_append_maps_source_and_requires_matching_identity(self):
        self.store.request.return_value = [{"event_id": "11111111-1111-4111-8111-111111111111"}]
        self.memory.append_event(self.valid_memory_event(), principal=self.astou)
        args = self.store.request.call_args.args
        self.assertEqual(args[0:2], ("POST", "papi_memory_events"))
        self.assertEqual(args[2]["source_type"], "task")
        self.assertEqual(args[2]["source_id"], "T-1")

    def test_memory_append_rejects_actor_spoofing_before_network(self):
        event = self.valid_memory_event()
        event["actor"] = "sokhna"
        with self.assertRaises(PermissionError):
            self.memory.append_event(event, principal=self.astou)
        self.store.request.assert_not_called()

    def test_memory_append_rejects_invalid_uuid_and_timestamp(self):
        event = self.valid_memory_event()
        event["event_id"] = "not-a-uuid"
        with self.assertRaises(SharedPersistenceError):
            self.memory.append_event(event, principal=self.astou)
        event = self.valid_memory_event()
        event["created_at"] = "2026-01-01T00:00:00"
        with self.assertRaises(SharedPersistenceError):
            self.memory.append_event(event, principal=self.astou)
        self.store.request.assert_not_called()

    def test_memory_append_rejects_secret_like_content(self):
        event = self.valid_memory_event()
        event["content"] = "api_key=super-secret-value"
        with self.assertRaises(SharedPersistenceError):
            self.memory.append_event(event, principal=self.astou)
        self.store.request.assert_not_called()

    def test_supersede_rejects_private_memory_owned_by_another_agent(self):
        event = {
            "event_id": "33333333-3333-4333-8333-333333333333",
            "event_type": "supersede", "target_memory_id": "22222222-2222-4222-8222-222222222222",
            "created_at": "2026-01-02T00:00:00Z", "actor": "astou", "reason": "archive",
        }
        self.store.request.return_value = [{
            "memory_id": event["target_memory_id"], "actor": "sokhna", "scope": "agent",
        }]
        with self.assertRaises(PermissionError):
            self.memory.append_event(event, principal=self.astou)

    def test_supersede_can_archive_visible_shared_memory(self):
        event = {
            "event_id": "33333333-3333-4333-8333-333333333333",
            "event_type": "supersede", "target_memory_id": "22222222-2222-4222-8222-222222222222",
            "created_at": "2026-01-02T00:00:00Z", "actor": "astou", "reason": "archive",
        }
        self.store.request.side_effect = [
            [{"memory_id": event["target_memory_id"], "actor": "sokhna", "scope": "shared"}],
            [{"event_id": event["event_id"]}],
        ]
        self.memory.append_event(event, principal=self.astou)
        self.assertEqual(self.store.request.call_count, 2)

    def test_memory_search_requires_authenticated_principal(self):
        with self.assertRaises(PermissionError):
            self.memory.search(principal="astou")

    def test_memory_search_filters_by_actor_and_hides_superseded(self):
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
        result = self.memory.search(principal=self.astou, query="current", category="fact")
        self.assertEqual([item["memory_id"] for item in result], ["m2"])
        query = self.store.request.call_args.args[1]
        self.assertIn("scope.eq.agent,actor.eq.astou", query)
        self.assertIn("event_type.eq.supersede", query)
        self.assertNotIn("category=eq.fact", query)

    def test_other_agent_cannot_hide_private_memory_with_supersede(self):
        rows = [
            {"event_type": "remember", "memory_id": "m3", "event_id": "e3",
             "created_at": "2026-01-03", "actor": "astou", "category": "fact",
             "title": "Private", "content": "private fact", "source_type": "task",
             "source_id": "T3", "confidence": 0.9, "scope": "agent",
             "tags": [], "sensitivity": "normal"},
            {"event_type": "supersede", "memory_id": "m3", "target_memory_id": "m3",
             "event_id": "e4", "created_at": "2026-01-04", "actor": "sokhna"},
        ]
        self.store.request.return_value = rows
        result = self.memory.search(principal=self.astou)
        self.assertEqual([item["memory_id"] for item in result], ["m3"])

    def test_memory_search_rejects_invalid_limit(self):
        with self.assertRaises(SharedPersistenceError):
            self.memory.search(principal=self.astou, limit=True)

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

    def test_chat_append_rejects_secret_like_content(self):
        message = self.valid_chat_message()
        message["body"] = "Bearer abcdefghijklmnopqrstuvwxyz1234"
        with self.assertRaises(SharedPersistenceError):
            self.chat.append_message(message)
        self.store.request.assert_not_called()

    def test_chat_read_rejects_raw_identity(self):
        with self.assertRaises(PermissionError):
            self.chat.read_messages(principal="astou")

    def test_chat_append_rejects_malformed_message_before_network(self):
        message = self.valid_chat_message()
        message["message_id"] = "MSG-invalid"
        with self.assertRaises(SharedPersistenceError):
            self.chat.append_message(message)
        self.store.request.assert_not_called()

    def test_chat_append_is_idempotent_for_identical_retry(self):
        message = self.valid_chat_message()
        self.store.request.side_effect = [[message], [], [message]]
        self.chat.append_message(message)
        self.chat.append_message(message)
        self.assertEqual(self.store.request.call_count, 3)
        self.assertEqual(
            self.store.request.call_args_list[1].kwargs["prefer"],
            "resolution=ignore-duplicates,return=representation",
        )
        self.assertIn("message_id=eq.", self.store.request.call_args_list[2].args[1])

    def test_chat_append_rejects_conflicting_duplicate_id(self):
        message = self.valid_chat_message()
        conflicting = dict(message, body="Different body")
        self.store.request.side_effect = [[message], [], [conflicting]]
        self.chat.append_message(message)
        with self.assertRaises(StoreError):
            self.chat.append_message(message)

    def test_append_requires_confirmed_insert(self):
        self.store.request.return_value = []
        with self.assertRaises(StoreError):
            self.chat.append_message(self.valid_chat_message())


if __name__ == "__main__":
    unittest.main()
