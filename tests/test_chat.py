import json
import tempfile
import unittest
from pathlib import Path

from papi_core.chat import ChatError, read_messages, send_message
from papi_core.identity_ed25519 import provision_ed25519_agent


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
        self.private_dir = self.root / "private"
        self.public_registry = self.root / "public-keys.json"
        self.replay_db = self.root / "replay.sqlite3"
        self.astou_key = provision_ed25519_agent("astou", self.private_dir, self.public_registry)
        self.owner_key = provision_ed25519_agent("owner", self.private_dir, self.public_registry)

    def tearDown(self):
        self.temp.cleanup()

    def send(self, **kwargs):
        kwargs.setdefault("private_key_path", self.astou_key if kwargs.get("sender", "astou") == "astou" else self.owner_key)
        kwargs.setdefault("path", self.messages)
        kwargs.setdefault("agents_path", self.agents)
        kwargs.setdefault("public_registry_path", self.public_registry)
        kwargs.setdefault("replay_db_path", self.replay_db)
        return send_message(**kwargs)

    def test_send_and_read_direct_message_with_signature(self):
        record = self.send(sender="astou", recipient="marietou", subject="Priorités",
                           body="Merci de vérifier les tâches ouvertes.")
        received = read_messages(recipient="marietou", path=self.messages,
                                 agents_path=self.agents, public_registry_path=self.public_registry)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["message"]["message_id"], record["message"]["message_id"])
        self.assertEqual(received[0]["auth"]["agent_id"], "astou")

    def test_broadcast_is_visible_to_agent(self):
        self.send(sender="owner", recipient="all", subject="Rappel",
                  body="Aucune dépense sans autorisation.",
                  private_key_path=self.owner_key)
        received = read_messages(recipient="astou", path=self.messages,
                                 agents_path=self.agents, public_registry_path=self.public_registry)
        self.assertEqual(len(received), 1)

    def test_unknown_recipient_and_secret_are_rejected(self):
        with self.assertRaises(ChatError):
            self.send(sender="astou", recipient="intrus", subject="Test", body="Bonjour")
        with self.assertRaises(ChatError):
            self.send(sender="astou", recipient="marietou", subject="Clé",
                      body="api_key=abc123secret")

    def test_unsigned_or_spoofed_message_is_rejected(self):
        with self.assertRaises(ChatError):
            send_message(sender="astou", recipient="marietou", subject="Usurpation",
                         body="Message sans clé", path=self.messages, agents_path=self.agents,
                         public_registry_path=self.public_registry, replay_db_path=self.replay_db)
        self.send(sender="astou", recipient="marietou", subject="Authentique", body="Bonjour")
        records = [json.loads(line) for line in self.messages.read_text(encoding="utf-8").splitlines()]
        records[0]["message"]["sender"] = "owner"
        self.messages.write_text(json.dumps(records[0]) + "\n", encoding="utf-8")
        with self.assertRaises(ChatError):
            read_messages(path=self.messages, agents_path=self.agents,
                          public_registry_path=self.public_registry)

    def test_tampered_body_is_rejected_on_read(self):
        self.send(sender="astou", recipient="marietou", subject="Sujet", body="Original")
        record = json.loads(self.messages.read_text(encoding="utf-8"))
        record["message"]["body"] = "Altéré"
        self.messages.write_text(json.dumps(record) + "\n", encoding="utf-8")
        with self.assertRaises(ChatError):
            read_messages(path=self.messages, agents_path=self.agents,
                          public_registry_path=self.public_registry)

    def test_repeated_reads_do_not_trigger_replay_error(self):
        self.send(sender="astou", recipient="marietou", subject="Sujet", body="Relisible")
        for _ in range(3):
            self.assertEqual(len(read_messages(
                recipient="marietou", path=self.messages, agents_path=self.agents,
                public_registry_path=self.public_registry)), 1)

    def test_limit_is_bounded(self):
        with self.assertRaises(ChatError):
            read_messages(limit=201, path=self.messages, agents_path=self.agents)

    def test_malformed_types_raise_chat_error_not_type_error(self):
        from papi_core.chat import _validate_message_fields
        valid = {
            "message_id": "MSG-" + "A" * 32,
            "sent_at": "2026-11-12T10:00:00Z",
            "sender": "astou", "recipient": "marietou", "subject": "Sujet",
            "body": "Message", "message_type": "info",
        }
        for field, value in (("sender", []), ("recipient", {}), ("subject", 4),
                             ("body", None), ("message_type", []), ("sent_at", 12)):
            candidate = dict(valid)
            candidate[field] = value
            with self.subTest(field=field):
                with self.assertRaises(ChatError):
                    _validate_message_fields(candidate, self.agents)

    def test_naive_timestamp_and_boolean_limit_are_rejected(self):
        from papi_core.chat import _validate_message_fields
        message = {
            "message_id": "MSG-" + "B" * 32,
            "sent_at": "2026-11-12T10:00:00", "sender": "astou",
            "recipient": "marietou", "subject": "Sujet", "body": "Message",
            "message_type": "info",
        }
        with self.assertRaises(ChatError):
            _validate_message_fields(message, self.agents)
        with self.assertRaises(ChatError):
            read_messages(limit=True, path=self.messages, agents_path=self.agents)


if __name__ == "__main__":
    unittest.main()
