import hashlib
import tempfile
import unittest
from pathlib import Path

from papi_core.papi_kids_release_report import (
    compose_kdp_readiness_report,
    save_kdp_readiness_report,
)


def fixture(root):
    upload = "PKP-UP-" + "e" * 32
    book = Path(root) / upload
    book.mkdir()
    package = book / "kdp-package-v001"
    package.mkdir()
    interior = package / "interior.pdf"
    cover = package / "cover.pdf"
    interior.write_bytes(b"%PDF-1.7\n/Type /Page\n" * 24)
    cover.write_bytes(b"%PDF-1.7\n/Type /Page\n")
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    package_manifest = {
        "upload_id": upload, "package_version": 1,
        "interior": {
            "path": f"{upload}/kdp-package-v001/interior.pdf",
            "sha256": digest(interior), "page_count": 24,
        },
        "cover": {
            "path": f"{upload}/kdp-package-v001/cover.pdf",
            "sha256": digest(cover), "page_count": 1,
        },
    }
    metadata = {
        "title": "Nia et la rivière aux mille reflets", "author": "Auteur confirmé",
        "language": "fr",
        "description": "Une histoire jeunesse complète et vérifiée pour les familles.",
        "keywords": ["jeunesse", "rivière"],
    }
    editorial = {"approved": True, "reviewer_id": "editor-01", "approved_at": "2026-11-15"}
    rights = {"commercial_use_confirmed": True, "rights_holder": "Auteur", "evidence_ref": "rights-01"}
    illustrations = [
        {"page_number": i, "review_status": "approved", "sha256": f"{i:064x}", "dpi": 300}
        for i in range(1, 25)
    ]
    print_spec = {
        "trim_size": "8.5x8.5", "paper_type": "white",
        "color_mode": "premium_color", "cover_template_sha256": "a" * 64,
    }
    account = {"eligibility_verified": True, "verified_at": "2026-11-15", "evidence_ref": "account-01"}
    pricing = {
        "verified": True, "marketplace": "Amazon.com", "currency": "USD",
        "list_price": 12.99, "estimated_print_cost": 4.5,
        "estimated_royalty": 3.29, "verified_at": "2026-11-15",
    }
    authorization = {"authorized": True, "authorization_ref": "owner-01", "authorized_at": "2026-11-15"}
    args = dict(
        book_id="PKP-0001", private_root=root, package_manifest=package_manifest,
        metadata=metadata, editorial_approval=editorial, rights=rights,
        illustrations=illustrations, print_spec=print_spec,
        kdp_account=account, pricing=pricing,
        publication_authorization=authorization,
    )
    attestations = {
        key: {"passed": True, "reviewer_id": "qa-01", "reviewed_at": "2026-11-15",
              "evidence_ref": f"qa-{key}-01"}
        for key in ("interior", "cover")
    }
    return upload, args, attestations


class PapiKidsReleaseReportTests(unittest.TestCase):
    def test_pending_visual_preflight_blocks_even_complete_package(self):
        with tempfile.TemporaryDirectory() as root:
            _, args, _ = fixture(root)
            report = compose_kdp_readiness_report(**args)
        self.assertFalse(report["publish_ready"])
        self.assertEqual(report["preflight_attestations"]["interior"]["status"], "pending")
        self.assertFalse(report["publication_execution_enabled"])

    def test_valid_human_preflight_can_reach_manual_submission_gate(self):
        with tempfile.TemporaryDirectory() as root:
            upload, args, attestations = fixture(root)
            report = compose_kdp_readiness_report(
                **args, preflight_attestations=attestations
            )
            path = save_kdp_readiness_report(root, upload, report)
            self.assertTrue(Path(path).is_file())
            self.assertEqual(Path(path).stat().st_mode & 0o777, 0o600)
        self.assertEqual(report["status"], "ready_for_manual_submission")
        self.assertFalse(report["publication_execution_enabled"])
        self.assertFalse(report["publication_performed"])

    def test_attestation_without_reviewer_or_evidence_does_not_pass(self):
        with tempfile.TemporaryDirectory() as root:
            _, args, attestations = fixture(root)
            attestations["cover"] = {"passed": True, "reviewer_id": "", "reviewed_at": "today"}
            report = compose_kdp_readiness_report(
                **args, preflight_attestations=attestations
            )
        self.assertFalse(report["publish_ready"])
        self.assertEqual(report["preflight_attestations"]["cover"]["status"], "pending")


if __name__ == "__main__":
    unittest.main()
