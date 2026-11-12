import unittest

from papi_core.agent_name_registry import (
    audit_legacy_name_collisions,
    normalize_name,
    validate_agent_name_registry,
)


class AgentNameRegistryTests(unittest.TestCase):
    def registry(self, agents):
        return {"schema_version": "1.0.0", "agents": agents}

    def agent(self, agent_id, given_name=None, full_name=None, **extra):
        return {
            "agent_id": agent_id,
            "given_name": given_name,
            "full_name": full_name,
            "aliases": [],
            "lifecycle_status": "planned",
            **extra,
        }

    def test_normalization_ignores_case_accents_and_separators(self):
        self.assertEqual(normalize_name("Élodie-Anne"), normalize_name("elodie anne"))

    def test_unassigned_planned_roles_are_allowed(self):
        self.assertEqual(
            validate_agent_name_registry(self.registry([self.agent("PAPI-001")])),
            [],
        )

    def test_duplicate_given_name_is_blocked_even_across_departments(self):
        errors = validate_agent_name_registry(self.registry([
            self.agent("PAPI-001", "Alex", "Alex Martin"),
            self.agent("PAPI-002", "ALEX", "Alex Brown"),
        ]))
        self.assertTrue(any("prénom dupliqué" in error for error in errors))

    def test_duplicate_full_name_is_blocked(self):
        errors = validate_agent_name_registry(self.registry([
            self.agent("PAPI-001", "Nora", "Nora Smith"),
            self.agent("PAPI-002", "Nora", "Nora Smith"),
        ]))
        self.assertTrue(any("prénom dupliqué" in error for error in errors))
        self.assertTrue(any("nom complet dupliqué" in error for error in errors))

    def test_existing_legacy_first_name_is_reserved(self):
        legacy = [{"id": "legacy-cheikh", "name": "Cheikh Fall"}]
        errors = validate_agent_name_registry(
            self.registry([self.agent("PAPI-001", "Cheikh", "Cheikh Diallo")]),
            legacy,
        )
        self.assertTrue(any("déjà réservé" in error for error in errors))

    def test_alias_and_transliteration_can_be_reserved_explicitly(self):
        legacy = [{"id": "legacy-alexander", "name": "Aleksandr", "aliases": ["Alexander"]}]
        errors = validate_agent_name_registry(
            self.registry([self.agent("PAPI-001", "Alexander", "Alexander Reed")]),
            legacy,
        )
        self.assertTrue(any("déjà réservé" in error for error in errors))

    def test_incomplete_identity_cannot_be_active(self):
        errors = validate_agent_name_registry(self.registry([
            self.agent("PAPI-001", "Lina", None, lifecycle_status="operational")
        ]))
        self.assertTrue(any("full_name obligatoire" in error for error in errors))

    def test_legacy_collision_audit_reports_duplicates(self):
        conflicts = audit_legacy_name_collisions([
            {"id": "cheikh", "name": "Cheikh"},
            {"id": "cheikh-fall", "name": "Cheikh Fall"},
        ])
        self.assertTrue(any(item["type"] == "given_name" for item in conflicts))


if __name__ == "__main__":
    unittest.main()
