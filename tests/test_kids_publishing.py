import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from papi_core.kids_publishing import (
    KidsPublishingError,
    _strict_json_bytes,
    build_catalog_report,
    check_book,
    inspect_book,
    validate_catalog,
)


class KidsPublishingTests(unittest.TestCase):
    def make_book(self, root: Path, **changes):
        files = {
            "manuscript": ("draft.md", b"# Original story\n"),
            "interior_pdf": ("interior.pdf", b"%PDF-interior"),
            "cover_pdf": ("cover.pdf", b"%PDF-cover"),
            "metadata": ("metadata.json", b'{"title":"Test"}'),
            "quality_report": ("quality.json", b'{"result":"passed"}'),
        }
        assets = []
        for kind, (name, content) in files.items():
            path = root / name
            path.write_bytes(content)
            assets.append({
                "kind": kind,
                "path": name,
                "sha256": hashlib.sha256(content).hexdigest(),
            })
        book = {
            "book_id": "PKP-TEST01",
            "title": "Une histoire originale",
            "language": "fr",
            "product_type": "illustrated_story",
            "format": "paperback",
            "target_age_min": 5,
            "target_age_max": 8,
            "workflow_stage": "quality_review",
            "original_work": True,
            "rights_status": "passed",
            "quality_status": "passed",
            "kdp_compliance_status": "passed",
            "human_approval": {"status": "pending"},
            "assets": assets,
        }
        book.update(changes)
        return book

    def test_empty_committed_catalog_is_valid(self):
        from papi_core.kids_publishing import CATALOG_FILE, load_catalog
        data = load_catalog(CATALOG_FILE)
        self.assertEqual(validate_catalog(data), [])
        self.assertEqual(data["books"], [])

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaises(KidsPublishingError):
            _strict_json_bytes(b'{"schema_version":1,"schema_version":1}')

    def test_non_standard_json_constant_is_rejected(self):
        with self.assertRaises(KidsPublishingError):
            _strict_json_bytes(b'{"value":NaN}')

    def test_invalid_age_range_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            book = self.make_book(root, target_age_min=9, target_age_max=4)
            self.assertTrue(any("inversée" in error for error in validate_catalog({
                "schema_version": 1, "division_id": "papi_kids_publishing", "books": [book]
            })))

    def test_duplicate_book_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            book = self.make_book(root)
            self.assertTrue(any("dupliqué" in error for error in validate_catalog({
                "schema_version": 1, "division_id": "papi_kids_publishing", "books": [book, book]
            })))

    def test_all_gates_pass_but_human_approval_still_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            book = self.make_book(root)
            result = inspect_book(book, root)
        self.assertTrue(result["valid"])
        self.assertTrue(result["ready_for_human_review"])
        self.assertIn("human_publication_approval_pending", result["blockers"])
        self.assertFalse(result["external_submission_performed"])
        self.assertFalse(result["external_publication_performed"])

    def test_human_approval_recorded_only_after_all_checks_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            book = self.make_book(root, human_approval={
                "status": "approved", "approved_by": "owner",
                "approved_at": "2026-11-15T12:00:00Z", "reference": "manual-review-001"
            })
            result = inspect_book(book, root)
        self.assertFalse(result["ready_for_human_review"])
        self.assertTrue(result["approved_for_manual_submission"])
        self.assertTrue(result["human_approval_recorded"])
        self.assertFalse(result["external_submission_performed"])

    def test_tampered_asset_digest_blocks_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            book = self.make_book(root)
            (root / "draft.md").write_text("changed", encoding="utf-8")
            result = inspect_book(book, root)
        self.assertIn("asset_manuscript_sha256_mismatch", result["blockers"])

    def test_missing_asset_blocks_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            book = self.make_book(root)
            (root / "cover.pdf").unlink()
            result = inspect_book(book, root)
        self.assertIn("asset_cover_pdf_missing_or_unreadable", result["blockers"])

    def test_symlink_asset_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            book = self.make_book(root)
            target = root / "real.pdf"
            target.write_bytes(b"%PDF")
            link = root / "linked.pdf"
            link.symlink_to(target)
            asset = next(item for item in book["assets"] if item["kind"] == "cover_pdf")
            asset["path"] = "linked.pdf"
            asset["sha256"] = hashlib.sha256(b"%PDF").hexdigest()
            result = inspect_book(book, root)
        self.assertIn("asset_cover_pdf_symlink_refused", result["blockers"])

    def test_ebook_does_not_require_print_cover_or_interior(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            book = self.make_book(root, format="ebook", assets=[
                asset for asset in self.make_book(root)["assets"]
                if asset["kind"] in {"manuscript", "metadata", "quality_report"}
            ])
            result = inspect_book(book, root)
        self.assertNotIn("asset_cover_pdf_missing_reference", result["blockers"])
        self.assertNotIn("asset_interior_pdf_missing_reference", result["blockers"])

    def test_malformed_enum_types_are_rejected_without_type_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            book = self.make_book(root, product_type=[], format={}, workflow_stage=[])
            errors = validate_catalog({
                "schema_version": 1, "division_id": "papi_kids_publishing", "books": [book]
            })
        self.assertTrue(any("product_type invalide" in error for error in errors))
        self.assertTrue(any("format invalide" in error for error in errors))
        self.assertTrue(any("workflow_stage invalide" in error for error in errors))

    def test_unhashable_asset_kind_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            book = self.make_book(root)
            book["assets"][0]["kind"] = []
            errors = validate_catalog({
                "schema_version": 1, "division_id": "papi_kids_publishing", "books": [book]
            })
        self.assertTrue(any("Type d'asset inconnu" in error for error in errors))

    def test_catalog_report_and_lookup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = root / "catalog.json"
            catalog.write_text(json.dumps({
                "schema_version": 1, "division_id": "papi_kids_publishing", "books": []
            }), encoding="utf-8")
            self.assertEqual(build_catalog_report(catalog)["total_books"], 0)
            with self.assertRaises(KidsPublishingError):
                check_book("PKP-MISSING", catalog)


if __name__ == "__main__":
    unittest.main()
