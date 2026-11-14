import unittest

from papi_core.human_handoff import (
    HumanHandoffError, close_handoff, confirm_user_action, create_handoff,
    resume_after_user_confirmation,
)


def handoff(**overrides):
    values = {
        "platform_id": "market.alpha",
        "platform_name": "Example AI platform",
        "official_url": "https://example.org/register",
        "required_user_action": "Créer le compte et effectuer la vérification KYC sur le site officiel.",
        "created_by_agent_id": "agent-aminata",
        "context": {"country": "SN", "payout_status": "needs_review"},
    }
    values.update(overrides)
    return create_handoff(**values)


class HumanHandoffTests(unittest.TestCase):
    def test_new_handoff_pauses_and_contains_no_credentials(self):
        result = handoff()
        self.assertEqual(result["status"], "awaiting_user")
        self.assertFalse(result["external_actions_performed"])
        self.assertIsNone(result["user_confirmation"])

    def test_confirmation_requires_waiting_state(self):
        item = handoff()
        confirmed = confirm_user_action(
            item, user_actor="owner", confirmation="Inscription terminée."
        )
        self.assertEqual(confirmed["status"], "user_confirmed")
        with self.assertRaises(HumanHandoffError):
            confirm_user_action(confirmed, user_actor="owner", confirmation="Encore.")

    def test_agent_cannot_resume_before_user_confirmation(self):
        with self.assertRaises(HumanHandoffError):
            resume_after_user_confirmation(handoff(), agent_id="agent-aminata")

    def test_resume_requires_user_attestation(self):
        item = confirm_user_action(
            handoff(), user_actor="owner", confirmation="Compte créé et KYC terminé."
        )
        resumed = resume_after_user_confirmation(item, agent_id="agent-aminata")
        self.assertEqual(resumed["status"], "resumed")
        self.assertEqual(resumed["resumed_by_agent_id"], "agent-aminata")

    def test_resumed_handoff_can_be_closed(self):
        item = confirm_user_action(
            handoff(), user_actor="owner", confirmation="Inscription terminée."
        )
        item = resume_after_user_confirmation(item, agent_id="agent-aminata")
        closed = close_handoff(item, actor="agent-aminata", outcome="completed")
        self.assertEqual(closed["status"], "completed")

    def test_sensitive_context_is_rejected(self):
        with self.assertRaises(HumanHandoffError):
            handoff(context={"password": "do-not-store"})

    def test_sensitive_confirmation_is_rejected(self):
        item = handoff()
        with self.assertRaises(HumanHandoffError):
            confirm_user_action(item, user_actor="owner", confirmation="OTP: 123456")

    def test_sensitive_confirmation_text_is_rejected(self):
        item = handoff()
        for phrase in ("OTP: 123456", "access token: secret", "refresh token=secret"):
            with self.subTest(phrase=phrase), self.assertRaises(HumanHandoffError):
                confirm_user_action(item, user_actor="owner", confirmation=phrase)

    def test_non_https_registration_url_is_rejected(self):
        with self.assertRaises(HumanHandoffError):
            handoff(official_url="http://example.org/register")


if __name__ == "__main__":
    unittest.main()
