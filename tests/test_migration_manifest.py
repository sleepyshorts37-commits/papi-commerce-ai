"""Tests for the offline Supabase migration inventory validator."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_migration_manifest", ROOT / "scripts" / "validate_migration_manifest.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MigrationManifestTests(unittest.TestCase):
    def test_repository_manifest_is_valid_and_emits_checksums(self):
        output = MODULE.validate()
        self.assertTrue(output)
        self.assertTrue(all("sha256=" in line for line in output))

    def test_migration_execution_must_remain_disabled(self):
        original = MODULE.MANIFEST.read_text(encoding="utf-8")
        try:
            data = json.loads(original)
            data["policy"]["execution_enabled"] = True
            with tempfile.TemporaryDirectory() as temp:
                manifest = Path(temp) / "manifest.json"
                manifest.write_text(json.dumps(data), encoding="utf-8")
                old = MODULE.MANIFEST
                MODULE.MANIFEST = manifest
                with self.assertRaisesRegex(ValueError, "execution must remain disabled"):
                    MODULE.validate()
                MODULE.MANIFEST = old
        finally:
            MODULE.MANIFEST = ROOT / "infra" / "supabase" / "migrations" / "manifest.json"

    def test_duplicate_or_unsorted_versions_are_rejected(self):
        original = MODULE.MANIFEST.read_text(encoding="utf-8")
        try:
            data = json.loads(original)
            data["migrations"].append(dict(data["migrations"][0]))
            with tempfile.TemporaryDirectory() as temp:
                manifest = Path(temp) / "manifest.json"
                manifest.write_text(json.dumps(data), encoding="utf-8")
                old = MODULE.MANIFEST
                MODULE.MANIFEST = manifest
                with self.assertRaisesRegex(ValueError, "unique and ascending"):
                    MODULE.validate()
                MODULE.MANIFEST = old
        finally:
            MODULE.MANIFEST = ROOT / "infra" / "supabase" / "migrations" / "manifest.json"


if __name__ == "__main__":
    unittest.main()
