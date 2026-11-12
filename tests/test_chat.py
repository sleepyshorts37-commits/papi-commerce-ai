import json
import tempfile
import unittest
from pathlib import Path

from papi_core.chat import ChatError, read_messages, send_message


class PapiChatTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.agents = self.root / "agents.json"
        self.agents.write_text(json.dumps({"agents": [
            {"id": "astou", "name": "Astou", "status": "defined"},
            {"id": "marietou", "name": "Marietou", "status": "planned"}
        ]}), encoding="utf-8")
        self.messages = self.root / "messages.jsonl"

    def tearDown(self):
        self.temp.cleanup()

    def test_send_and_read_direct_message(self):
        message = send_message(
            sender="astou", recipient="marietou", subject="Priorités",
            body="Merci de vérifier les tâches ouvertes.",
            path=self.messages, agents_path=self.agents
        )
        received = read_messages(recipient="marietou", path=self.messages, agents_path=self.agents)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["message_id"], message["message_id"])

    def test_broadcast_is_visible_to_agent(self):
        send_message(
            sender="owner", recipient="all", subject="Rappel",
            body="Aucune dépense sans autorisation.",
            path=self.messages, agents_path=self.agents
        )
        self.assertEqual(len(read_messages(recipient="astou", path=self.messages, agents_path=self.agents)), 1)

    def test_unknown_recipient_and_secret_are_rejected(self):
        with self.assertRaises(ChatError):
            send_message(sender="astou", recipient="intrus", subject="Test", body="Bonjour",
                         path=self.messages, agents_path=self.agents)
        with self.assertRaises(ChatError):
            send_message(sender="astou", recipient="marietou", subject="Clé",
                         body="api_key=abc123secret", path=self.messages, agents_path=self.agents)

    def test_limit_is_bounded(self):
        with self.assertRaises(ChatError):
            read_messages(limit=201, path=self.messages, agents_path=self.agents)


    def test_malformed_types_raise_chat_error_not_type_error(self):
        from papi_core.chat import validate_message
        valid = {
            "message_id": "MSG-" + "A" * 32,
            "sent_at": "2026-11-12T10:00:00Z",
            "sender": "astou",
            "recipient": "marietou",
            "subject": "Sujet",
            "body": "Message",
            "message_type": "info",
        }
        for field, value in (("sender", []), ("recipient", {}), ("subject", 4),
                             ("body", None), ("message_type", []), ("sent_at", 12)):
            candidate = dict(valid)
            candidate[field] = value
            with self.subTest(field=field):
                with self.assertRaises(ChatError):
                    validate_message(candidate, self.agents)

    def test_naive_timestamp_and_boolean_limit_are_rejected(self):
        from papi_core.chat import validate_message
        message = {
            "message_id": "MSG-" + "B" * 32,
            "sent_at": "2026-11-12T10:00:00",
            "sender": "astou",
            "recipient": "marietou",
            "subject": "Sujet",
            "body": "Message",
            "message_type": "info",
        }
        with self.assertRaises(ChatError):
            validate_message(message, self.agents)
        with self.assertRaises(ChatError):
            read_messages(limit=True, path=self.messages, agents_path=self.agents)


if __name__ == "__main__":
    unittest.main()
