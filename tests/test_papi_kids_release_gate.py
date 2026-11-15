import hashlib
import tempfile
import unittest
from pathlib import Path

from papi_core.papi_kids_release_gate import evaluate_kdp_release_gate


def complete_manifest(root):
    interior = Path(root) / "interior.pdf"
    cover = Path(root) / "cover.pdf"
    interior.write_bytes(b"%PDF-1.7\n/Type /Page\n" * 24)
    cover.write_bytes(b"%PDF-1.7\n/Type /Page\n")
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "metadata": {
            "title": "Nia et la rivière aux mille reflets",
            "author": "Auteur confirmé",
            "language": "fr",
            "description": "Une histoire jeunesse complète et vérifiée pour les familles.",
            "keywords": ["jeunesse", "rivière"],
        },
        "editorial_approval": {"approved": True, "reviewer_id": "editor-01", "approved_at": "2026-11-15"},
        "rights": {"commercial_use_confirmed": True, "rights_holder": "Auteur", "evidence_ref": "rights-001"},
        "page_count": 24,
        "illustrations": [
            {"page_number": i, "review_status": "approved", "sha256": f"{i:064x}", "dpi": 300}
            for i in range(1, 25)
        ],
        "pdfs": {
            "interior": {"path": "interior.pdf", "sha256": digest(interior), "page_count": 24, "preflight": "passed"},
            "cover": {"path": "cover.pdf", "sha256": digest(cover), "page_count": 1, "preflight": "passed"},
        },
        "print_spec": {
            "trim_size": "8.5x8.5", "paper_type": "white",
            "color_mode": "premium_color", "cover_template_sha256": "a" * 64,
        },
        "kdp_account": {"eligibility_verified": True, "verified_at": "2026-11-15", "evidence_ref": "account-check-001"},
        "pricing": {
            "verified": True, "marketplace": "Amazon.com", "currency": "USD",
            "list_price": 12.99, "estimated_print_cost": 4.5,
            "estimated_royalty": 3.29, "verified_at": "2026-11-15",
        },
        "publication_authorization": {
            "authorized": True, "authorization_ref": "owner-approval-001",
            "authorized_at": "2026-11-15",
        },
        "spend_limit_minor": 0,
    }


class PapiKidsReleaseGateTests(unittest.TestCase):
    def test_missing_manifest_is_blocked(self):
        result = evaluate_kdp_release_gate(book_id="PKP-0001", manifest={}, private_root="/tmp")
        self.assertFalse(result["publish_ready"])
        self.assertFalse(result["publication_execution_enabled"])
        self.assertGreater(result["blocker_count"], 0)

    def test_complete_manifest_is_ready_for_manual_submission_only(self):
        with tempfile.TemporaryDirectory() as root:
            manifest = complete_manifest(root)
            result = evaluate_kdp_release_gate(
                book_id="PKP-0001", manifest=manifest, private_root=root,
            )
        self.assertEqual(result["status"], "ready_for_manual_submission", result["blockers"])
        self.assertTrue(result["publish_ready"])
        self.assertFalse(result["publication_execution_enabled"])
        self.assertFalse(result["publication_performed"])

    def test_unapproved_image_and_missing_owner_authorization_block_release(self):
        with tempfile.TemporaryDirectory() as root:
            manifest = complete_manifest(root)
            manifest["illustrations"][0]["review_status"] = "pending_review"
            manifest["publication_authorization"]["authorized"] = False
            result = evaluate_kdp_release_gate(
                book_id="PKP-0001", manifest=manifest, private_root=root,
            )
        self.assertFalse(result["publish_ready"])
        self.assertTrue(any("Illustration page 1" in item for item in result["blockers"]))
        self.assertTrue(any("Autorisation explicite" in item for item in result["blockers"]))

    def test_pdf_hash_mismatch_blocks_release(self):
        with tempfile.TemporaryDirectory() as root:
            manifest = complete_manifest(root)
            manifest["pdfs"]["cover"]["sha256"] = "0" * 64
            result = evaluate_kdp_release_gate(
                book_id="PKP-0001", manifest=manifest, private_root=root,
            )
        self.assertFalse(result["publish_ready"])
        self.assertTrue(any("SHA-256 du PDF cover" in item for item in result["blockers"]))


if __name__ == "__main__":
    unittest.main()
