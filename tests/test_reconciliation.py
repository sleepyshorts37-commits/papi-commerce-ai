import unittest

from papi_core.principal import _issue_authenticated_agent_principal
from papi_core.reconciliation import ReconciliationError, build_reconciliation_preview


class ReconciliationPreviewTests(unittest.TestCase):
    def setUp(self):
        self.principal = _issue_authenticated_agent_principal("astou")
        self.memory = {
            "memory_id": "MEM-001", "event_type": "remember", "scope": "shared",
            "sensitivity": "normal", "category": "fact", "title": "Procédure",
            "content": "Contrôle validé.", "source_type": "test", "source_id": "case-1",
            "confidence": 0.9, "tags": [],
        }
        self.message = {
            "message_id": "MSG-001", "sender": "astou", "recipient": "all",
            "subject": "Rapport", "body": "Rapport prêt.", "message_type": "report",
        }

    def preview(self, **overrides):
        args = dict(local_memory=[self.memory], remote_memory=[self.memory],
                    local_messages=[self.message], remote_messages=[self.message])
        args.update(overrides)
        return build_reconciliation_preview(principal=self.principal, **args)

    def test_identical_records_are_reported_without_writes(self):
        result = self.preview()
        self.assertEqual(result["mode"], "preview_only")
        self.assertFalse(result["writes_performed"])
        self.assertEqual(result["counts"]["identical"], 2)
        self.assertFalse(result["requires_human_review"])

    def test_local_only_and_remote_only_are_candidates_not_transfers(self):
        result = self.preview(remote_memory=[], local_messages=[], remote_messages=[self.message])
        self.assertEqual(result["counts"]["local_only"], 1)
        self.assertEqual(result["counts"]["remote_only"], 1)
        self.assertTrue(result["requires_human_review"])
        self.assertFalse(result["writes_performed"])

    def test_same_identifier_with_different_payload_is_conflict(self):
        changed = {**self.memory, "content": "Version différente."}
        result = self.preview(remote_memory=[changed])
        self.assertEqual(result["counts"]["conflicts"], 1)
        self.assertEqual(result["memory"]["conflicts"][0]["record_id"], "MEM-001")

    def test_private_memory_and_other_recipient_messages_are_excluded(self):
        private = {**self.memory, "memory_id": "MEM-PRIVATE", "scope": "agent"}
        private_message = {**self.message, "message_id": "MSG-PRIVATE", "recipient": "marietou"}
        result = self.preview(local_memory=[self.memory, private], remote_memory=[self.memory],
                              local_messages=[self.message, private_message],
                              remote_messages=[self.message])
        self.assertEqual(result["counts"]["identical"], 2)
        self.assertEqual(result["counts"]["local_only"], 0)

    def test_secrets_and_duplicate_identifiers_are_rejected(self):
        secret = {**self.memory, "content": "password=super-secret"}
        with self.assertRaises(ReconciliationError):
            self.preview(local_memory=[secret])
        with self.assertRaises(ReconciliationError):
            self.preview(local_memory=[self.memory, self.memory])

    def test_authentication_is_mandatory(self):
        with self.assertRaises(PermissionError):
            build_reconciliation_preview(principal="astou", local_memory=[], remote_memory=[],
                                        local_messages=[], remote_messages=[])


if __name__ == "__main__":
    unittest.main()
