import unittest

from papi_core.principal import _issue_authenticated_agent_principal
from papi_core.shared_collaboration import SharedCollaborationError, SharedCollaborationStore


class FakeStore:
    def __init__(self):
        self.calls = []
        self.rows = []

    def _request(self, method, path, payload=None, prefer=None):
        self.calls.append((method, path, payload))
        if method == "POST":
            self.rows.append(payload)
            return [payload]
        if "papi_memory_events" in path and "target_memory_id" in path:
            return []
        if "papi_memory_events" in path:
            if "scope=eq.shared" in path:
                return [row for row in self.rows if row.get("scope") == "shared" and row.get("event_type") == "remember"]
            actor = path.split("actor=eq.", 1)[1].split("&", 1)[0]
            return [row for row in self.rows if row.get("scope") == "agent" and row.get("actor") == actor]
        if "papi_chat_messages" in path:
            recipient = path.split("recipient.eq.", 1)[1].split(")", 1)[0]
            return [row for row in self.rows if row.get("recipient") in {"all", recipient}]
        return []


class SharedCollaborationAdapterTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeStore()
        self.adapter = SharedCollaborationStore(store=self.fake)
        self.astou = _issue_authenticated_agent_principal("astou")
        self.marietou = _issue_authenticated_agent_principal("marietou")

    def test_store_must_be_injected_and_principal_is_mandatory(self):
        with self.assertRaises(SharedCollaborationError):
            SharedCollaborationStore(store=None)
        with self.assertRaises(PermissionError):
            self.adapter.read_messages(principal="astou")

    def test_memory_write_uses_authenticated_actor_and_scope_filter(self):
        self.adapter.remember(principal=self.astou, category="fact", title="Règle",
                               content="Contrôle validé.", source_type="test",
                               source_id="case-1", scope="agent")
        self.assertEqual(self.fake.rows[0]["actor"], "astou")
        self.assertEqual(self.fake.rows[0]["scope"], "agent")
        self.adapter.search_memory(principal=self.marietou)
        self.assertIn("actor=eq.marietou", self.fake.calls[-2][1])

    def test_decisions_and_secrets_are_rejected(self):
        with self.assertRaises(SharedCollaborationError):
            self.adapter.remember(principal=self.astou, category="decision", title="Décision",
                                  content="Non.", source_type="test", source_id="case")
        with self.assertRaises(ValueError):
            self.adapter.remember(principal=self.astou, category="fact", title="Clé",
                                  content="Bearer abcdefghijklmnop", source_type="test",
                                  source_id="case")

    def test_chat_sender_is_bound_to_principal_and_reads_are_server_filtered(self):
        message = self.adapter.send_message(principal=self.astou, recipient="marietou",
                                            subject="Tâche", body="Vérifier le rapport.")
        self.assertEqual(message["sender"], "astou")
        self.adapter.read_messages(principal=self.marietou)
        self.assertIn("recipient.eq.marietou", self.fake.calls[-1][1])

    def test_invalid_recipient_and_limit_are_rejected(self):
        with self.assertRaises(SharedCollaborationError):
            self.adapter.send_message(principal=self.astou, recipient="bad recipient",
                                      subject="Test", body="Bonjour")
        with self.assertRaises(SharedCollaborationError):
            self.adapter.read_messages(principal=self.astou, limit=201)


if __name__ == "__main__":
    unittest.main()
