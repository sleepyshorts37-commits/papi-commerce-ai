import json
import tempfile
import unittest
from pathlib import Path

from papi_core.registry import validate_agent_directory


class AgentDirectoryTests(unittest.TestCase):
    def _write(self, root: Path, agents):
        path = root / "agents.json"
        path.write_text(json.dumps({"agents": agents}, ensure_ascii=False), encoding="utf-8")
        return path

    def _agent(self, **changes):
        value = {
            "id": "agent-one",
            "name": "Aïcha",
            "role": "Recherche",
            "department": "Recherche",
            "status": "planned",
            "permissions": ["read_reports"],
            "prohibited": ["spend_money"],
        }
        value.update(changes)
        return value

    def test_current_registry_has_unique_valid_agent_identities(self):
        report = validate_agent_directory()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["agent_count"], 40)
        self.assertGreater(report["department_count"], 1)
        self.assertEqual(report["status_counts"]["defined"], 3)
        self.assertEqual(report["status_counts"]["planned"], 37)

    def test_duplicate_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), [self._agent(), self._agent(name="Awa")])
            report = validate_agent_directory(path)
            self.assertFalse(report["valid"])
            self.assertTrue(any("Identifiant d'agent dupliqué" in item for item in report["errors"]))

    def test_names_colliding_after_case_accent_and_space_normalization_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), [
                self._agent(id="agent-one", name="Aïcha"),
                self._agent(id="agent-two", name="  AICHA  "),
            ])
            report = validate_agent_directory(path)
            self.assertFalse(report["valid"])
            self.assertTrue(any("Nom affiché ambigu" in item for item in report["errors"]))

    def test_invalid_fields_and_duplicate_permissions_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), [
                self._agent(id="Bad ID", role="", status="unknown",
                            permissions=["read_reports", "read_reports"],
                            prohibited="spend_money", manager_agent_id="missing"),
            ])
            report = validate_agent_directory(path)
            self.assertFalse(report["valid"])
            self.assertGreaterEqual(len(report["errors"]), 5)

    def test_unknown_manager_reference_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), [
                self._agent(manager_agent_id="not-in-registry"),
            ])
            report = validate_agent_directory(path)
            self.assertFalse(report["valid"])
            self.assertTrue(any("Responsable hiérarchique inconnu" in item for item in report["errors"]))

    def test_empty_registry_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), [])
            with self.assertRaises(ValueError):
                validate_agent_directory(path)


if __name__ == "__main__":
    unittest.main()
