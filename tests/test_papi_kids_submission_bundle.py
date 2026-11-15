import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock

from papi_core.papi_kids_submission_bundle import (
    PapiKidsSubmissionBundleError,
    build_private_kdp_submission_bundle,
)


class KdpSubmissionBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.upload = "PKP-UP-" + "a" * 32
        self.book_dir = self.root / self.upload
        package_dir = self.book_dir / "package-v001"
        package_dir.mkdir(parents=True)
        interior = b"%PDF-1.7 interior"
        cover = b"%PDF-1.7 cover"
        (package_dir / "interior.pdf").write_bytes(interior)
        (package_dir / "cover.pdf").write_bytes(cover)
        self.hashes = {
            "interior": hashlib.sha256(interior).hexdigest(),
            "cover": hashlib.sha256(cover).hexdigest(),
        }
        self.manifest = {
            "upload_id": self.upload, "package_version": 1, "spend_limit_minor": 0,
            "pdfs": {
                "interior": {"path": f"{self.upload}/package-v001/interior.pdf", "sha256": self.hashes["interior"]},
                "cover": {"path": f"{self.upload}/package-v001/cover.pdf", "sha256": self.hashes["cover"]},
            },
        }
        self.manifest_hash = hashlib.sha256(json.dumps(
            self.manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest()
        self.metadata = {
            "kdp_owner_release_authorization": {
                "package_version": 1, "manifest_sha256": self.manifest_hash,
                "owner_id": "owner-01", "manual_submission_only": True,
                "confirmed_at": "2026-11-15", "evidence_ref": "d" * 64,
            },
            "kdp_package_reviews": {
                f"v1:{kind}": {"approved": True, "decision": "approved",
                               "package_version": 1, "artifact_sha256": digest,
                               "reviewer_id": "qa-01", "evidence_ref": "e" * 64}
                for kind, digest in self.hashes.items()
            },
            "content_safety_review": {"approved": True, "reviewer_id": "qa-01"},
            "kdp_listing_metadata": {
                "title": "Nia", "author": "Auteur", "description": "Une histoire illustrée pour enfants. " * 4,
                "language": "fr", "keywords": ["rivière"], "categories": ["Enfants"],
                "reading_age_min": 4, "reading_age_max": 8,
                "commercial_use_confirmed": True, "rights_holder": "Auteur",
                "rights_evidence_ref": "contrat-01", "territories": "worldwide",
                "isbn_strategy": "kdp_free_isbn", "marketplace": "amazon.fr",
                "currency": "EUR", "list_price": 9.99,
                "pricing_verified": True, "pricing_verified_at": "2026-11-15",
            },
        }
        self.connection = Mock()
        self.connection.cursor.return_value.fetchone.side_effect = [
            ("book-uuid", self.metadata, 1, self.manifest, self.manifest_hash),
            ("authorization-uuid",),
        ]

    def tearDown(self):
        self.temp.cleanup()

    def test_exports_hash_verified_pdf_files_and_audit_documents(self):
        callback = build_private_kdp_submission_bundle(self.root, lambda: self.connection)
        result = callback(self.upload)
        self.assertEqual(result["content_type"], "application/zip")
        self.assertFalse(result["publication_performed"])
        with zipfile.ZipFile(io.BytesIO(result["data"])) as archive:
            names = set(archive.namelist())
            self.assertIn("interior.pdf", names)
            self.assertIn("cover.pdf", names)
            self.assertIn("package-manifest.json", names)
            self.assertIn("kdp-listing-metadata.json", names)
            self.assertIn("review-attestations.json", names)
            self.assertIn("SHA256SUMS.txt", names)
            self.assertEqual(archive.read("interior.pdf"), b"%PDF-1.7 interior")
        self.assertEqual(self.connection.commit.call_count, 1)

    def test_rejects_missing_owner_authorization(self):
        self.metadata["kdp_owner_release_authorization"] = {}
        callback = build_private_kdp_submission_bundle(self.root, lambda: self.connection)
        with self.assertRaises(PapiKidsSubmissionBundleError):
            callback(self.upload)
        self.assertEqual(self.connection.rollback.call_count, 1)

    def test_rejects_artifact_hash_mismatch(self):
        (self.book_dir / "package-v001" / "interior.pdf").write_bytes(b"%PDF-1.7 altered")
        callback = build_private_kdp_submission_bundle(self.root, lambda: self.connection)
        with self.assertRaises(PapiKidsSubmissionBundleError):
            callback(self.upload)

    def test_rejects_path_traversal(self):
        self.manifest["pdfs"]["interior"]["path"] = "../../etc/passwd"
        self.connection.cursor.return_value.fetchone.side_effect = [
            ("book-uuid", self.metadata, 1, self.manifest, self.manifest_hash),
            ("authorization-uuid",),
        ]
        self.manifest_hash = hashlib.sha256(json.dumps(
            self.manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest()
        self.metadata["kdp_owner_release_authorization"]["manifest_sha256"] = self.manifest_hash
        callback = build_private_kdp_submission_bundle(self.root, lambda: self.connection)
        with self.assertRaises(PapiKidsSubmissionBundleError):
            callback(self.upload)


if __name__ == "__main__":
    unittest.main()
