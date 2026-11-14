import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from papi_core import chat
from papi_core.chat import ChatError, read_messages, send_message


class PapiChatJournalIntegrityTests(unittest.TestCase):
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

    def event(self, **changes):
        event = {
            "message_id": "MSG-12345678123456781234567812345678",
            "sent_at": "2026-11-14T10:00:00Z",
            "sender": "astou", "recipient": "marietou",
            "subject": "Compte rendu", "body": "Contrôle effectué.",
            "message_type": "report",
        }
        event.update(changes)
        return event

    def write(self, *events):
        self.messages.write_text("".join(json.dumps(item) + "\n" for item in events), encoding="utf-8")

    def test_duplicate_message_ids_are_rejected(self):
        self.write(self.event(), self.event(subject="Deuxième message"))
        with self.assertRaises(ChatError):
            read_messages(path=self.messages, agents_path=self.agents)

    def test_naive_timestamp_is_rejected(self):
        self.write(self.event(sent_at="2026-11-14T10:00:00"))
        with self.assertRaises(ChatError):
            read_messages(path=self.messages, agents_path=self.agents)

    def test_malformed_uuid_is_rejected(self):
        self.write(self.event(message_id="MSG-not-a-uuid"))
        with self.assertRaises(ChatError):
            read_messages(path=self.messages, agents_path=self.agents)

    def test_blank_line_is_rejected(self):
        self.messages.write_text(json.dumps(self.event()) + "\n\n", encoding="utf-8")
        with self.assertRaises(ChatError):
            read_messages(path=self.messages, agents_path=self.agents)

    def test_unhashable_message_type_is_rejected_cleanly(self):
        self.write(self.event(message_type=[]))
        with self.assertRaises(ChatError):
            read_messages(path=self.messages, agents_path=self.agents)

    def test_partial_os_writes_are_completed(self):
        real_write = os.write
        calls = []

        def partial_write(fd, payload):
            calls.append(len(payload))
            return real_write(fd, payload[:max(1, len(payload) // 2)])

        with patch.object(chat.os, "write", side_effect=partial_write):
            sent = send_message(sender="astou", recipient="marietou", subject="Essai",
                                body="Écriture partielle", path=self.messages, agents_path=self.agents)
        stored = read_messages(path=self.messages, agents_path=self.agents)
        self.assertEqual(stored, [sent])
        self.assertGreater(len(calls), 1)

    def test_message_id_requires_uuid_hex_after_prefix(self):
        with self.assertRaises(ChatError):
            chat.validate_message(self.event(message_id="MSG-1234"), self.agents)


if __name__ == "__main__":
    unittest.main()
