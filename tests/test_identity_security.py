import unittest

from runtime.papi_core.identity_security import (
    authorize_agent_action, identity_fingerprint, validate_identity_registry,
    verify_identity,
)


def identity(**changes):
    value = {
        "identity_id": "PAPI-ID-DEMO", "agent_id": "demo",
        "full_name": "Demo Agent", "role": "Tester", "department": "QA",
        "manager_id": None, "mission": "Test identity", "competencies": [],
        "objectives": [], "autonomy_level": "none", "permissions": ["read_reports"],
        "prohibited_actions": ["spend_money"], "status": "active",
        "created_at": "2026-01-01T00:00:00Z", "assignment_history": [],
        "evaluation_history": [], "profile_state": "complete",
    }
    value.update(changes)
    return value


class IdentitySecurityTests(unittest.TestCase):
    def test_registry_rejects_duplicate_ids(self):
        doc = {"identities": [identity(), identity(identity_id="PAPI-ID-OTHER")]}
        with self.assertRaises(ValueError):
            validate_identity_registry(doc)

    def test_registry_accepts_unique_complete_schema(self):
        result = validate_identity_registry({"identities": [identity()]})
        self.assertTrue(result["valid"])
        self.assertEqual(result["identities_count"], 1)

    def test_fingerprint_detects_change(self):
        original = identity()
        expected = identity_fingerprint(original)
        self.assertTrue(verify_identity(original, expected_fingerprint=expected)["integrity_match"])
        changed = identity(role="Different")
        self.assertFalse(verify_identity(changed, expected_fingerprint=expected)["integrity_match"])

    def test_permission_allow_requires_all_gates(self):
        item = identity()
        result = authorize_agent_action(
            item, registry_agent={"id": "demo", "status": "active"},
            requested_permission="read_reports",
            expected_fingerprint=identity_fingerprint(item),
        )
        self.assertEqual(result["decision"], "allow")
        self.assertFalse(result["action_executed"])

    def test_default_deny_for_unlisted_or_prohibited_permission(self):
        item = identity()
        for permission in ("send_messages", "spend_money"):
            result = authorize_agent_action(
                item, registry_agent={"id": "demo", "status": "active"},
                requested_permission=permission,
                expected_fingerprint=identity_fingerprint(item),
            )
            self.assertEqual(result["decision"], "deny")

    def test_planned_or_incomplete_agent_is_denied(self):
        item = identity(status="planned", profile_state="incomplete")
        result = authorize_agent_action(
            item, registry_agent={"id": "demo", "status": "planned"},
            requested_permission="read_reports",
            expected_fingerprint=identity_fingerprint(item),
        )
        self.assertEqual(result["decision"], "deny")
        self.assertIn("agent_not_active", result["reasons"])


if __name__ == "__main__":
    unittest.main()
