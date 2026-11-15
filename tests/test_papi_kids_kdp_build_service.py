import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from papi_core.papi_kids_kdp_build_service import (
    PapiKidsKDPBuildServiceError,
    build_kdp_package_from_private_profile,
)


class PapiKidsKDPBuildServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.upload = "PKP-UP-" + "a" * 32
        self.book = self.root / self.upload
        self.book.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def write_config(self, config):
        path = self.book / "kdp-build-config.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        os.chmod(path, 0o600)
        return path

    def test_build_requires_private_profile(self):
        with self.assertRaises(PapiKidsKDPBuildServiceError):
            build_kdp_package_from_private_profile(self.root, self.upload)

    def test_build_calls_package_builder_only_with_server_profile(self):
        config = {
            "package_version": 2,
            "interior_args": {"pages": [{"page_number": i} for i in range(24)], "assets": []},
            "cover_args": {"page_count": 24},
            "ebook_args": None,
            "ebook_required": False,
        }
        self.write_config(config)
        result = {
            "package_dir": str(self.book / "package-v002"),
            "manifest_path": str(self.book / "package-v002" / "package-manifest.json"),
            "manifest": {"package_version": 2},
            "status": "generated_pending_manual_pdf_inspection",
        }
        with patch("papi_core.papi_kids_kdp_build_service.build_kdp_print_package", return_value=result) as build:
            response = build_kdp_package_from_private_profile(self.root, self.upload)
        self.assertEqual(response["status"], "generated_pending_manual_pdf_inspection")
        self.assertFalse(response["kdp_upload_ready"])
        self.assertEqual(build.call_args.kwargs["package_version"], 2)
        self.assertEqual(build.call_args.kwargs["storage_root"], self.root.resolve())

    def test_profile_with_secret_or_public_permissions_is_rejected(self):
        path = self.write_config({
            "interior_args": {"pages": []}, "cover_args": {},
            "token": "should-never-be-here",
        })
        with self.assertRaises(PapiKidsKDPBuildServiceError):
            build_kdp_package_from_private_profile(self.root, self.upload)
        path = self.write_config({"interior_args": {}, "cover_args": {}})
        os.chmod(path, 0o644)
        with self.assertRaises(PapiKidsKDPBuildServiceError):
            build_kdp_package_from_private_profile(self.root, self.upload)

    def test_profile_rejects_unknown_fields_and_large_files(self):
        path = self.write_config({"interior_args": {}, "cover_args": {}, "unknown": True})
        with self.assertRaises(PapiKidsKDPBuildServiceError):
            build_kdp_package_from_private_profile(self.root, self.upload)
        path.write_text(" " * (256 * 1024 + 1), encoding="utf-8")
        with self.assertRaises(PapiKidsKDPBuildServiceError):
            build_kdp_package_from_private_profile(self.root, self.upload)


if __name__ == "__main__":
    unittest.main()
