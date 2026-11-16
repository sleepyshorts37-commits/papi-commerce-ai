import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from papi_core.papi_kids_readiness import (
    REQUIRED_TABLES, REQUIRED_TRIGGERS, check_papi_kids_readiness,
)


def configured_environment():
    return {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "s" * 40,
        "PAPI_KIDS_UPLOAD_TOKEN": "u" * 40,
        "PAPI_KIDS_REVIEW_TOKEN": "r" * 40,
        "PAPI_KIDS_SAFETY_REVIEW_TOKEN": "s" * 40,
        "PAPI_KIDS_METADATA_TOKEN": "m" * 40,
        "PAPI_KIDS_KDP_BUILD_TOKEN": "b" * 40,
        "PAPI_KIDS_KDP_REVIEW_TOKEN": "k" * 40,
        "PAPI_KIDS_KINDLE_PREVIEWER_TOKEN": "p" * 40,
        "PAPI_KIDS_OWNER_RELEASE_TOKEN": "o" * 40,
        "PAPI_KIDS_RELEASE_OWNER_ID": "owner-01",
        "PAPI_KIDS_REVIEWER_ID": "owner-01",
        "PAPI_KIDS_METADATA_EDITOR_ID": "owner-01",
        "CLOUDFLARE_ACCOUNT_ID": "a" * 32,
        "CLOUDFLARE_API_TOKEN": "c" * 40,
        "PAPI_KIDS_KDP_BUILD_ENABLED": "false",
    }


class PapiKidsReadinessTests(unittest.TestCase):
    def test_reports_missing_configuration_without_secret_values(self):
        with tempfile.TemporaryDirectory() as root:
            os.chmod(root, 0o700)
            connection = MagicMock()
            connection.cursor.return_value.fetchone.return_value = (1,)
            connection.cursor.return_value.fetchall.return_value = []
            with patch.dict(os.environ, {}, clear=True):
                result = check_papi_kids_readiness(
                    storage_root=root, connection_factory=lambda: connection,
                )
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["secrets_returned"])
        self.assertIn("SUPABASE_URL", result["checks"]["core_secrets"]["missing"])
        self.assertFalse(result["checks"]["image_provider"]["quota_verified"])
        self.assertEqual(result["spend_limit_minor"], 0)

    def test_reports_ready_core_when_tables_and_immutable_audit_trigger_exist(self):
        with tempfile.TemporaryDirectory() as root:
            os.chmod(root, 0o700)
            cursor = MagicMock()
            cursor.fetchone.return_value = (1,)
            cursor.fetchall.side_effect = [
                [(name,) for name in sorted(REQUIRED_TABLES)],
                [(name,) for name in sorted(REQUIRED_TRIGGERS)],
            ]
            connection = MagicMock()
            connection.cursor.return_value = cursor
            with patch.dict(os.environ, configured_environment(), clear=True):
                result = check_papi_kids_readiness(
                    storage_root=root, connection_factory=lambda: connection,
                )
        self.assertTrue(result["core_ready"])
        self.assertTrue(result["owner_workflows_ready"])
        self.assertTrue(result["image_generation_ready"])
        self.assertFalse(result["package_build_enabled"])
        self.assertFalse(result["external_provider_calls"])
        self.assertEqual(result["checks"]["database"]["missing_required_triggers"], [])

    def test_missing_lifecycle_append_only_trigger_blocks_core_readiness(self):
        with tempfile.TemporaryDirectory() as root:
            os.chmod(root, 0o700)
            cursor = MagicMock()
            cursor.fetchone.return_value = (1,)
            cursor.fetchall.side_effect = [
                [(name,) for name in sorted(REQUIRED_TABLES)],
                [],
            ]
            connection = MagicMock()
            connection.cursor.return_value = cursor
            with patch.dict(os.environ, configured_environment(), clear=True):
                result = check_papi_kids_readiness(
                    storage_root=root, connection_factory=lambda: connection,
                )
        self.assertFalse(result["core_ready"])
        self.assertEqual(
            result["checks"]["database"]["missing_required_triggers"],
            ["kdp_submission_lifecycle_events_append_only"],
        )
        self.assertTrue(any("append-only" in item for item in result["blockers"]))

    def test_storage_permissions_must_be_private(self):
        with tempfile.TemporaryDirectory() as root:
            os.chmod(root, 0o755)
            connection = MagicMock()
            connection.cursor.return_value.fetchone.return_value = (1,)
            connection.cursor.return_value.fetchall.return_value = []
            with patch.dict(os.environ, {}, clear=True):
                result = check_papi_kids_readiness(
                    storage_root=root, connection_factory=lambda: connection,
                )
        self.assertFalse(result["checks"]["private_storage"]["private_permissions"])
        self.assertTrue(any("mode 0700" in item for item in result["blockers"]))


if __name__ == "__main__":
    unittest.main()
