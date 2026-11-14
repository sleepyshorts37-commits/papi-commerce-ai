import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from papi_core.principal import _issue_authenticated_agent_principal
from papi_core.storage import StoreError, SupabaseStore


class CollaborationSyncTests(unittest.TestCase):
    def setUp(self):
        self.store = SupabaseStore(url="https://example.supabase.co", key="test-server-key")
        self.store._request = Mock()
        self.principal = _issue_authenticated_agent_principal("astou")

    def test_memory_append_maps_source_and_is_idempotent(self):
        event = {
            "event_id": "11111111-1111-4111-8111-111111111111",
            "memory_id": "22222222-2222-4222-8222-222222222222",
            "event_type": "remember", "created_at": "2026-11-14T10:00:00Z",
            "actor": "astou", "category": "fact", "title": "Décision", "content": "Contenu sûr",
            "source": {"type": "test", "id": "fixture-001"}, "confidence": 0.9,
            "scope": "shared", "tags": ["ci"], "sensitivity": "normal",
        }
        self.store._request.return_value = []
        result = self.store.sync_memory_event(event, principal=self.principal)
        self.assertTrue(result["duplicate"])
        args = self.store._request.call_args
        self.assertEqual(args.args[1], "papi_memory_events?on_conflict=idempotency_key")
        self.assertEqual(args.args[2]["source_type"], "test")
        self.assertEqual(args.args[2]["actor"], "astou")
        self.assertNotIn("source", args.args[2])

    def test_memory_actor_mismatch_is_rejected_before_network(self):
        with self.assertRaises(StoreError):
            self.store.sync_memory_event({"actor": "intruder"}, principal=self.principal)
        self.store._request.assert_not_called()

    def test_chat_requires_matching_authenticated_sender(self):
        with tempfile.TemporaryDirectory() as directory:
            agents = Path(directory) / "agents.json"
            agents.write_text('{"agents":[{"id":"astou","name":"Astou","status":"active"}]}', encoding="utf-8")
            message = {
                "message_id": "MSG-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                "sent_at": "2026-11-14T10:00:00Z", "sender": "astou", "recipient": "all",
                "subject": "Rapport", "body": "Message interne de test.", "message_type": "info",
            }
            self.store._request.return_value = [{"message_id": message["message_id"]}]
            result = self.store.sync_chat_message(message, principal=self.principal, agents_path=agents)
            self.assertTrue(result["synced"])
            self.assertEqual(self.store._request.call_args.args[1], "papi_chat_messages?on_conflict=idempotency_key")

    def test_chat_rejects_sender_spoofing(self):
        with self.assertRaises(StoreError):
            self.store.sync_chat_message({"sender": "marietou"}, principal=self.principal)
        self.store._request.assert_not_called()

    def test_keyset_memory_page_returns_next_cursor(self):
        self.store._request.return_value = [
            {"event_id": "e3", "created_at": "2026-11-14T10:03:00Z"},
            {"event_id": "e2", "created_at": "2026-11-14T10:02:00Z"},
            {"event_id": "e1", "created_at": "2026-11-14T10:01:00Z"},
        ]
        page = self.store.page_memory_events(principal=self.principal, limit=2)
        self.assertEqual([x["event_id"] for x in page["items"]], ["e3", "e2"])
        self.assertTrue(page["next_cursor"])
        self.store._request.reset_mock()
        self.store._request.return_value = []
        self.store.page_memory_events(principal=self.principal, limit=2, cursor=page["next_cursor"])
        self.assertEqual(self.store._request.call_args.args[1], "rpc/papi_list_memory_events")
        self.assertEqual(self.store._request.call_args.args[2]["p_before_event_id"], "e2")

    def test_keyset_chat_page_and_invalid_cursor(self):
        self.store._request.return_value = [
            {"message_id": "MSG-CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC", "sent_at": "2026-11-14T10:03:00Z"},
            {"message_id": "MSG-BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB", "sent_at": "2026-11-14T10:02:00Z"},
        ]
        page = self.store.page_chat_messages(principal=self.principal, limit=1)
        self.assertEqual(len(page["items"]), 1)
        self.assertTrue(page["next_cursor"])
        with self.assertRaises(StoreError):
            self.store.page_chat_messages(principal=self.principal, cursor="not-a-valid-cursor")

    def test_list_scope_filters_use_authenticated_actor(self):
        self.store._request.return_value = []
        self.store.list_memory_events(principal=self.principal)
        self.assertEqual(self.store._request.call_args.args[1], "rpc/papi_list_memory_events")
        self.assertEqual(self.store._request.call_args.args[2]["p_actor"], "astou")
        self.store._request.reset_mock()
        self.store.list_chat_messages(principal=self.principal)
        self.assertIn("recipient.eq.astou", self.store._request.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
