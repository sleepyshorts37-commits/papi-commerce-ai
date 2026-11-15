import hashlib
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED

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
        "kdp_listing_metadata": {
            "title": "Nia et la rivière aux mille reflets",
            "author": "Auteur confirmé",
            "description": "Une histoire jeunesse complète et vérifiée pour les familles.",
            "language": "fr",
            "keywords": ["jeunesse", "rivière"],
            "categories": ["Children's Books / Environment"],
            "reading_age_min": 5, "reading_age_max": 8,
            "commercial_use_confirmed": True,
            "rights_holder": "Auteur", "rights_evidence_ref": "rights-001",
            "territories": "worldwide",
            "isbn_strategy": "kdp_free_isbn",
            "marketplace": "Amazon.com", "currency": "USD",
            "list_price": 12.99, "pricing_verified": True,
            "pricing_verified_at": "2026-11-15",
        },
        "manuscript_sha256": "b" * 64,
        "content_safety_review": {
            "approved": True, "reviewer_id": "safety-01", "reviewed_at": "2026-11-15",
            "evidence_ref": "safety-review-01", "manuscript_sha256": "b" * 64,
        },
        "page_count": 24,
        "illustrations": [
            {"page_number": i, "review_status": "approved", "sha256": f"{i:064x}", "dpi": 300,
             "source_width_px": 2550, "source_height_px": 2550,
             "width_px": 2550, "height_px": 2550, "upscaling_method": "native"}
            for i in range(1, 25)
        ],
        "package_version": 1,
        "kdp_package_reviews": {
            "v1:interior": {
                "package_version": 1, "artifact": "interior",
                "artifact_sha256": digest(interior), "decision": "approved", "approved": True,
                "reviewer_id": "owner-01", "reviewed_at": "2026-11-15",
                "evidence_ref": "a" * 64,
                "notes": "PDF intérieur inspecté page par page, marges et images vérifiées.",
            },
            "v1:cover": {
                "package_version": 1, "artifact": "cover",
                "artifact_sha256": digest(cover), "decision": "approved", "approved": True,
                "reviewer_id": "owner-01", "reviewed_at": "2026-11-15",
                "evidence_ref": "b" * 64,
                "notes": "Couverture inspectée, dos, fonds perdus et textes contrôlés.",
            },
        },
        "pdfs": {
            "interior": {"path": "interior.pdf", "sha256": digest(interior), "page_count": 24, "preflight": "automated_checks_passed_pending_human_review"},
            "cover": {"path": "cover.pdf", "sha256": digest(cover), "page_count": 1, "preflight": "automated_checks_passed_pending_human_review"},
        },
        "print_spec": {
            "trim_size": "8.5x8.5", "trim_width_in": 8.5, "trim_height_in": 8.5,
            "bleed": False, "paper_type": "white",
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
        self.assertEqual(result["status"], "ready_for_manual_submission")
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

    def test_lanczos_upscale_cannot_pass_print_release_gate(self):
        with tempfile.TemporaryDirectory() as root:
            manifest = complete_manifest(root)
            for asset in manifest["illustrations"]:
                asset["source_width_px"] = 1024
                asset["source_height_px"] = 1024
                asset["upscaling_method"] = "lanczos_only"
            result = evaluate_kdp_release_gate(
                book_id="PKP-0001", manifest=manifest, private_root=root,
            )
        self.assertFalse(result["publish_ready"])
        self.assertTrue(any("super-résolution" in item for item in result["blockers"]))

    def create_valid_epub(self, path):
        with ZipFile(path, "w") as archive:
            archive.writestr("mimetype", "application/epub+zip", compress_type=ZIP_STORED)
            archive.writestr("META-INF/container.xml",
                '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/package.opf"/></rootfiles></container>',
                compress_type=ZIP_DEFLATED)
            archive.writestr("OEBPS/package.opf",
                '<package xmlns="http://www.idpf.org/2007/opf"><metadata/><manifest/><spine/><meta property="rendition:layout">pre-paginated</meta></package>',
                compress_type=ZIP_DEFLATED)
            archive.writestr("OEBPS/nav.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml"><body><nav/></body></html>', compress_type=ZIP_DEFLATED)
            archive.writestr("OEBPS/styles/book.css", "body{}")
            archive.writestr("OEBPS/pages/cover.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml"><body/></html>')
            for number in range(1, 25):
                archive.writestr(
                    f"OEBPS/pages/page-{number:03d}.xhtml",
                    '<html xmlns="http://www.w3.org/1999/xhtml"><body><a class="app-amzn-magnify"/></body></html>',
                )

    def test_ebook_required_blocks_without_kindle_previewer_review(self):
        with tempfile.TemporaryDirectory() as root:
            manifest = complete_manifest(root)
            epub_path = Path(root) / "book.epub"
            self.create_valid_epub(epub_path)
            digest = hashlib.sha256(epub_path.read_bytes()).hexdigest()
            manifest["ebook_required"] = True
            manifest["ebook"] = {
                "path": "book.epub", "sha256": digest, "page_count": 24,
                "preflight": "automated_epub_checks_passed_pending_kindle_previewer", "format": "EPUB 3 fixed-layout",
            }
            result = evaluate_kdp_release_gate(
                book_id="PKP-0001", manifest=manifest, private_root=root,
            )
        self.assertFalse(result["publish_ready"])
        self.assertTrue(any("Kindle Previewer" in item for item in result["blockers"]))

    def test_ebook_passes_only_with_preview_attestation_bound_to_epub_hash(self):
        with tempfile.TemporaryDirectory() as root:
            manifest = complete_manifest(root)
            epub_path = Path(root) / "book.epub"
            self.create_valid_epub(epub_path)
            digest = hashlib.sha256(epub_path.read_bytes()).hexdigest()
            manifest["ebook_required"] = True
            manifest["ebook"] = {
                "path": "book.epub", "sha256": digest, "page_count": 24,
                "preflight": "passed", "format": "EPUB 3 fixed-layout",
            }
            manifest["kdp_package_reviews"]["v1:ebook"] = {
                "package_version": 1, "artifact": "ebook",
                "artifact_sha256": digest, "decision": "approved", "approved": True,
                "reviewer_id": "owner-01", "reviewed_at": "2026-11-15",
                "evidence_ref": "c" * 64,
                "notes": "EPUB contrôlé dans le lecteur, navigation et illustrations vérifiées.",
            }
            manifest["kindle_previewer_review"] = {
                "passed": True, "package_version": 1, "reviewer_id": "qa-01", "reviewed_at": "2026-11-15",
                "evidence_ref": "d" * 64, "epub_sha256": digest,
                "notes": "Kindle Previewer vérifié, navigation et rendu contrôlés.",
            }
            result = evaluate_kdp_release_gate(
                book_id="PKP-0001", manifest=manifest, private_root=root,
            )
        self.assertTrue(result["publish_ready"])
        self.assertEqual(result["ebook"]["status"], "approved")
        self.assertFalse(result["publication_execution_enabled"])

    def test_ebook_preview_attestation_for_different_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            manifest = complete_manifest(root)
            epub_path = Path(root) / "book.epub"
            self.create_valid_epub(epub_path)
            digest = hashlib.sha256(epub_path.read_bytes()).hexdigest()
            manifest["ebook_required"] = True
            manifest["ebook"] = {
                "path": "book.epub", "sha256": digest, "page_count": 24,
                "preflight": "passed", "format": "EPUB 3 fixed-layout",
            }
            manifest["kindle_previewer_review"] = {
                "passed": True, "package_version": 1, "reviewer_id": "qa-01", "reviewed_at": "2026-11-15",
                "evidence_ref": "d" * 64, "epub_sha256": "0" * 64,
                "notes": "Kindle Previewer vérifié, navigation et rendu contrôlés.",
            }
            result = evaluate_kdp_release_gate(
                book_id="PKP-0001", manifest=manifest, private_root=root,
            )
        self.assertFalse(result["publish_ready"])
        self.assertTrue(any("Kindle Previewer" in item for item in result["blockers"]))

    def test_missing_or_stale_child_safety_review_blocks_release(self):
        with tempfile.TemporaryDirectory() as root:
            manifest = complete_manifest(root)
            manifest["content_safety_review"]["manuscript_sha256"] = "c" * 64
            result = evaluate_kdp_release_gate(
                book_id="PKP-0001", manifest=manifest, private_root=root,
            )
        self.assertFalse(result["publish_ready"])
        self.assertTrue(any("sécurité jeunesse" in item for item in result["blockers"]))

    def test_missing_listing_category_blocks_release(self):
        with tempfile.TemporaryDirectory() as root:
            manifest = complete_manifest(root)
            manifest["kdp_listing_metadata"]["categories"] = []
            result = evaluate_kdp_release_gate(
                book_id="PKP-0001", manifest=manifest, private_root=root,
            )
        self.assertFalse(result["publish_ready"])
        self.assertTrue(any("catégories KDP" in item for item in result["blockers"]))

    def test_listing_metadata_price_must_match_verified_pricing(self):
        with tempfile.TemporaryDirectory() as root:
            manifest = complete_manifest(root)
            manifest["kdp_listing_metadata"]["list_price"] = 14.99
            result = evaluate_kdp_release_gate(
                book_id="PKP-0001", manifest=manifest, private_root=root,
            )
        self.assertFalse(result["publish_ready"])
        self.assertTrue(any("divergent" in item for item in result["blockers"]))

    def test_missing_or_stale_pdf_inspection_attestation_blocks_release(self):
        with tempfile.TemporaryDirectory() as root:
            manifest = complete_manifest(root)
            manifest["kdp_package_reviews"].pop("v1:interior")
            result = evaluate_kdp_release_gate(
                book_id="PKP-0001", manifest=manifest, private_root=root,
            )
        self.assertFalse(result["publish_ready"])
        self.assertTrue(any("Revue humaine du fichier interior absente" in item for item in result["blockers"]))

        with tempfile.TemporaryDirectory() as root:
            manifest = complete_manifest(root)
            manifest["kdp_package_reviews"]["v1:cover"]["artifact_sha256"] = "0" * 64
            result = evaluate_kdp_release_gate(
                book_id="PKP-0001", manifest=manifest, private_root=root,
            )
        self.assertFalse(result["publish_ready"])
        self.assertTrue(any("autre version ou empreinte" in item for item in result["blockers"]))

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
