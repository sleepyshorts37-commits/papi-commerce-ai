import unittest

from runtime.papi_core.agent_messaging import (
    AgentMessagingError, build_message_candidate, build_message_center,
)


def identity(agent_id, status="active", permissions=None, profile_state="complete"):
    return {
        "identity_id": f"PAPI-ID-{agent_id.upper()}", "agent_id": agent_id,
        "full_name": agent_id, "role": "Test", "department": "QA",
        "manager_id": None, "mission": "Test", "competencies": [],
        "objectives": [], "autonomy_level": "none",
        "permissions": permissions or ["send_internal_messages"],
        "prohibited_actions": [], "status": status,
        "created_at": "2026-01-01T00:00:00Z", "assignment_history": [],
        "evaluation_history": [], "profile_state": profile_state,
    }


def setup_data(sender=None):
    sender = sender or identity("sender")
    receiver = identity("receiver", status="planned", permissions=[])
    doc = {"identities": [sender, receiver]}
    agents = {
        "sender": {"id": "sender", "status": sender["status"]},
        "receiver": {"id": "receiver", "status": "planned"},
    }
    return doc, agents


class AgentMessagingTests(unittest.TestCase):
    def test_candidate_is_draft_only(self):
        doc, agents = setup_data()
        result = build_message_candidate(
            sender_id="sender", recipient_id="receiver", message_type="report",
            subject="Rapport", body="État du projet", priority="normal",
            created_at="2026-11-12T10:00:00Z", message_id="MSG-001",
            identity_document=doc, agents=agents,
        )
        self.assertEqual(result["status"], "draft_candidate")
        self.assertFalse(result["persisted"])
        self.assertFalse(result["delivered"])

    def test_inactive_sender_is_denied(self):
        sender = identity("sender", status="planned")
        doc, agents = setup_data(sender)
        with self.assertRaises(AgentMessagingError):
            build_message_candidate(
                sender_id="sender", recipient_id="receiver", message_type="question",
                subject="Q", body="Test", priority="low",
                created_at="2026-11-12T10:00:00Z", message_id="MSG-002",
                identity_document=doc, agents=agents,
            )

    def test_missing_permission_is_denied(self):
        sender = identity("sender", permissions=["read_reports"])
        doc, agents = setup_data(sender)
        with self.assertRaises(AgentMessagingError):
            build_message_candidate(
                sender_id="sender", recipient_id="receiver", message_type="question",
                subject="Q", body="Test", priority="low",
                created_at="2026-11-12T10:00:00Z", message_id="MSG-003",
                identity_document=doc, agents=agents,
            )

    def test_unknown_recipient_and_personal_data_are_denied(self):
        doc, agents = setup_data()
        args = dict(sender_id="sender", message_type="report", subject="Rapport",
                    priority="normal", created_at="2026-11-12T10:00:00Z",
                    message_id="MSG-004", identity_document=doc, agents=agents)
        with self.assertRaises(AgentMessagingError):
            build_message_candidate(recipient_id="missing", body="Test", **args)
        with self.assertRaises(AgentMessagingError):
            build_message_candidate(recipient_id="receiver", body="Contact test@example.com", **args)

    def test_center_ignores_unrelated_events(self):
        doc, _ = setup_data()
        result = build_message_center([], doc)
        self.assertEqual(result["message_count"], 0)
        self.assertFalse(result["delivery_enabled"])


if __name__ == "__main__":
    unittest.main()
