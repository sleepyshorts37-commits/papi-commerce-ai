import unittest

from papi_core.agent_identity_card import (
    IdentityCardError, create_identity_card, validate_identity_card,
)


class AgentIdentityCardTests(unittest.TestCase):
    def setUp(self):
        self.agent = {
            "id": "astou", "name": "Astou", "role": "Coordination",
            "department": "Direction", "status": "defined",
            "permissions": ["read_reports", "prepare_priorities"],
            "skills": ["analyse", "coordination"],
        }

    def test_creates_unique_professional_card_without_activating_agent(self):
        card = create_identity_card(self.agent, "2026-11-12", "president")
        validate_identity_card(card)
        self.assertEqual(card["employee_id"], "PAPI-AG-ASTOU")
        self.assertEqual(card["manager_agent_id"], "president")
        self.assertEqual(card["status"], "defined")
        self.assertEqual(card["autonomy_level"], "bounded")
        self.assertEqual(card["permissions"], self.agent["permissions"])

    def test_new_agent_can_receive_a_distinct_card(self):
        first = create_identity_card(self.agent, "2026-11-12")
        second_agent = {**self.agent, "id": "astou-research", "name": "Astou Research"}
        second = create_identity_card(second_agent, "2026-11-12", "astou")
        self.assertNotEqual(first["employee_id"], second["employee_id"])

    def test_rejects_missing_or_invalid_identity_fields(self):
        for changes in (
            {"id": ""},
            {"permissions": ["read_reports", None]},
            {"status": "unknown"},
            {"status": ["defined"]},
            {"permissions": ["   "]},
            {"autonomy_level": "unlimited"},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(IdentityCardError):
                    create_identity_card({**self.agent, **changes}, "2026-11-12")

    def test_rejects_malformed_unhashable_status_without_type_error(self):
        with self.assertRaises(IdentityCardError):
            create_identity_card({**self.agent, "status": []}, "2026-11-12")

    def test_rejects_invalid_creation_date(self):
        with self.assertRaises(IdentityCardError):
            create_identity_card(self.agent, "tomorrow")

    def test_rejects_self_manager_and_malformed_manager(self):
        for manager in ("astou", "bad manager", ""):
            with self.subTest(manager=manager):
                with self.assertRaises(IdentityCardError):
                    create_identity_card(self.agent, "2026-11-12", manager)

    def test_rejects_duplicate_permissions_and_skills(self):
        for changes in (
            {"permissions": ["read_reports", "read_reports"]},
            {"skills": ["analyse", "analyse"]},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(IdentityCardError):
                    create_identity_card({**self.agent, **changes}, "2026-11-12")

    def test_validator_rejects_tampered_manager_skills_and_history(self):
        card = create_identity_card(self.agent, "2026-11-12", "president")
        for field, value in (
            ("manager_agent_id", "astou"),
            ("skills", ["analyse", None]),
            ("employment_history", [{"role": "Direction", "status": "active", "date": "not-a-date"}]),
            ("employment_history", ["promoted"]),
        ):
            altered = {**card, field: value}
            with self.subTest(field=field, value=value):
                with self.assertRaises(IdentityCardError):
                    validate_identity_card(altered)

    def test_accepts_structured_employment_history(self):
        card = create_identity_card(self.agent, "2026-11-12", "president")
        card["employment_history"] = [
            {"role": "Analyste", "status": "planned", "date": "2026-11-12"}
        ]
        validate_identity_card(card)

    def test_validation_detects_tampered_employee_identifier(self):
        card = create_identity_card(self.agent, "2026-11-12")
        card["employee_id"] = "PAPI-AG-OTHER"
        with self.assertRaises(IdentityCardError):
            validate_identity_card(card)


if __name__ == "__main__":
    unittest.main()
