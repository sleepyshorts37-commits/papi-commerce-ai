import unittest

from papi_core.principal import _issue_authenticated_agent_principal
from papi_core.shared_collaboration import SharedCollaborationError, SharedCollaborationStore


class FakeStore:
    def __init__(self):
        self.calls = []
        self.rows = {"papi_memory_events": [], "papi_chat_messages": []}

    def _request(self, method, path, payload=None, prefer=None):
        self.calls.append((method, path, payload, prefer))
        table = "papi_memory_events" if "papi_memory_events" in path else "papi_chat_messages"
        rows = self.rows[table]
        if method == "POST":
            key = payload["idempotency_key"]
            existing = [row for row in rows if row.get("idempotency_key") == key]
            if existing:
                return []
            rows.append(payload)
            return [payload]
        if "idempotency_key=eq." in path:
            key = path.split("idempotency_key=eq.", 1)[1].split("&", 1)[0]
            return [row for row in rows if row.get("idempotency_key") == key]
        if "target_memory_id=in.(" in path:
            return []
        if table == "papi_memory_events":
            filtered = [row for row in rows if row.get("event_type") == "remember"]
            if "scope=eq.shared" in path:
                filtered = [row for row in filtered if row.get("scope") == "shared"]
            if "actor=eq." in path:
                actor = path.split("actor=eq.", 1)[1].split("&", 1)[0]
                filtered = [row for row in filtered if row.get("scope") == "agent" and row.get("actor") == actor]
            if "created_at.lt." in path:
                stamp = path.split("created_at.lt.", 1)[1].split(",", 1)[0]
                filtered = [row for row in filtered if row["created_at"] < stamp]
            return sorted(filtered, key=lambda row: (row["created_at"], row["event_id"]), reverse=True)
        filtered = [row for row in rows if row.get("recipient") == "all" or "recipient.eq." + row.get("recipient", "") in path]
        if "sent_at.lt." in path:
            stamp = path.split("sent_at.lt.", 1)[1].split(",", 1)[0]
            filtered = [row for row in filtered if row["sent_at"] < stamp]
        return sorted(filtered, key=lambda row: (row["sent_at"], row["message_id"]), reverse=True)


class SharedCollaborationAdapterTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeStore()
        self.adapter = SharedCollaborationStore(store=self.fake)
        self.astou = _issue_authenticated_agent_principal("astou")
        self.marietou = _issue_authenticated_agent_principal("marietou")

    def test_store_and_authenticated_principal_are_required(self):
        with self.assertRaises(SharedCollaborationError):
            SharedCollaborationStore(store=None)
        with self.assertRaises(PermissionError):
            self.adapter.read_messages(principal="astou")

    def test_memory_write_is_scoped_and_idempotent(self):
        args = dict(principal=self.astou, category="fact", title="Règle",
                    content="Contrôle validé.", source_type="test", source_id="case-1",
                    scope="agent", idempotency_key="memory-key-0001")
        first = self.adapter.remember(**args)
        second = self.adapter.remember(**args)
        self.assertEqual(first["event_id"], second["event_id"])
        self.assertEqual(len(self.fake.rows["papi_memory_events"]), 1)
        self.assertEqual(first["actor"], "astou")
        self.adapter.search_memory(principal=self.marietou)
        self.assertIn("actor=eq.marietou", self.fake.calls[-2][1])

    def test_reusing_idempotency_key_with_different_payload_is_rejected(self):
        args = dict(principal=self.astou, category="fact", title="Règle",
                    content="Contrôle validé.", source_type="test", source_id="case-1",
                    idempotency_key="memory-key-0002")
        self.adapter.remember(**args)
        with self.assertRaises(SharedCollaborationError):
            self.adapter.remember(**{**args, "content": "Autre contenu."})

    def test_secrets_and_decision_category_are_rejected(self):
        args = dict(principal=self.astou, title="Décision", content="Non.",
                    source_type="test", source_id="case", idempotency_key="memory-key-0003")
        with self.assertRaises(SharedCollaborationError):
            self.adapter.remember(**args, category="decision")
        with self.assertRaises(ValueError):
            self.adapter.remember(**{**args, "title": "Clé", "content": "Bearer abcdefghijklmnop"},
                                  category="fact")

    def test_chat_write_is_idempotent_and_recipient_filtered(self):
        args = dict(principal=self.astou, recipient="marietou", subject="Tâche",
                    body="Vérifier le rapport.", idempotency_key="message-key-0001")
        first = self.adapter.send_message(**args)
        second = self.adapter.send_message(**args)
        self.assertEqual(first["message_id"], second["message_id"])
        self.assertEqual(len(self.fake.rows["papi_chat_messages"]), 1)
        self.assertEqual(first["sender"], "astou")
        self.adapter.read_messages(principal=self.marietou)
        self.assertIn("recipient.eq.marietou", self.fake.calls[-1][1])

    def test_memory_and_chat_return_stable_next_cursors(self):
        for index in range(3):
            self.adapter.remember(
                principal=self.astou, category="fact", title=f"Memory {index}",
                content="pagination test", source_type="test", source_id=f"source-{index}",
                idempotency_key=f"memory-page-{index:04d}",
            )
            self.adapter.send_message(
                principal=self.astou, recipient="all", subject=f"Message {index}",
                body="pagination test", idempotency_key=f"message-page-{index:04d}",
            )
        memory_first = self.adapter.search_memory(principal=self.astou, limit=2)
        chat_first = self.adapter.read_messages(principal=self.astou, limit=2)
        self.assertEqual(len(memory_first["items"]), 2)
        self.assertTrue(memory_first["next_cursor"])
        self.assertEqual(len(chat_first["items"]), 2)
        self.assertTrue(chat_first["next_cursor"])
        memory_second = self.adapter.search_memory(
            principal=self.astou, limit=2, cursor=memory_first["next_cursor"]
        )
        chat_second = self.adapter.read_messages(
            principal=self.astou, limit=2, cursor=chat_first["next_cursor"]
        )
        self.assertEqual(len(memory_second["items"]), 1)
        self.assertEqual(len(chat_second["items"]), 1)

    def test_invalid_keys_limits_and_cursors_are_rejected(self):
        with self.assertRaises(SharedCollaborationError):
            self.adapter.send_message(principal=self.astou, recipient="bad recipient",
                                      subject="Test", body="Bonjour",
                                      idempotency_key="short")
        with self.assertRaises(SharedCollaborationError):
            self.adapter.read_messages(principal=self.astou, limit=201)
        with self.assertRaises(SharedCollaborationError):
            self.adapter.search_memory(principal=self.astou, cursor="not-a-cursor")


if __name__ == "__main__":
    unittest.main()
