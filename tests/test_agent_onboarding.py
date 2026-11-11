import json
import tempfile
import unittest
from pathlib import Path

from papi_core.agent_onboarding import OnboardingError, prepare_agent_onboarding


class AgentOnboardingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry = Path(self.tmp.name) / "agents.json"
        self.registry.write_text(json.dumps({"agents": [
            {"id": "astou", "name": "Astou", "role": "Coordination",
             "department": "Direction", "status": "defined",
             "permissions": ["read_reports"], "prohibited": []}
        ]}), encoding="utf-8")
        self.args = dict(
            agent_id="new-researcher", name="Researcher",
            role="Analyste marché", department="PAPI MARKET",
            mission="Repérer et évaluer des opportunités commerciales.",
            manager_agent_id="astou", created_at="2026-11-12",
            agents_path=self.registry, skills=["recherche", "analyse"],
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_prepares_candidate_with_unique_card_and_no_activation(self):
        result = prepare_agent_onboarding(**self.args)
        self.assertEqual(result["onboarding_status"], "prepared")
        self.assertEqual(result["activation_status"], "not_activated")
        self.assertEqual(result["profile"]["status"], "planned")
        self.assertEqual(result["identity_card"]["employee_id"], "PAPI-AG-NEW-RESEARCHER")
        self.assertEqual(result["identity_card"]["manager_agent_id"], "astou")
        self.assertEqual(result["profile"]["permissions"], [])
        # Preparation is a proposal only: the live registry is unchanged.
        self.assertNotIn("new-researcher", json.loads(self.registry.read_text())["agents"][0])

    def test_rejects_duplicate_identifier(self):
        args = {**self.args, "agent_id": "astou"}
        with self.assertRaises(OnboardingError):
            prepare_agent_onboarding(**args)

    def test_rejects_missing_or_suspended_manager(self):
        args = {**self.args, "manager_agent_id": "missing"}
        with self.assertRaises(OnboardingError):
            prepare_agent_onboarding(**args)

    def test_rejects_invalid_permission_and_duplicate_permissions(self):
        for permissions in (["read_reports", None], ["read_reports", "read_reports"]):
            with self.subTest(permissions=permissions):
                with self.assertRaises(OnboardingError):
                    prepare_agent_onboarding(**self.args, permissions=permissions)

    def test_rejects_invalid_date_and_identity(self):
        with self.assertRaises(OnboardingError):
            prepare_agent_onboarding(**{**self.args, "created_at": "soon"})
        with self.assertRaises(OnboardingError):
            prepare_agent_onboarding(**{**self.args, "agent_id": ""})


if __name__ == "__main__":
    unittest.main()
