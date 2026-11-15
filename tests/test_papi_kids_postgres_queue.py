import unittest
from unittest.mock import Mock

from papi_core.papi_kids_postgres_queue import (
    PostgresEditorialQueueError,
    enqueue_manuscript,
    claim_editorial_job,
    complete_editorial_job,
    fail_editorial_job,
    record_manuscript_safety_review,
    record_kdp_listing_metadata,
    record_kdp_package_build,
    record_kdp_package_review,
)


class FakeConnection:
    def __init__(self, rows=()):
        self.cursor_obj = Mock()
        self.cursor_obj.fetchone.side_effect = list(rows)
        self.cursor_obj.description = [("job_id",), ("status",)]
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class PostgresEditorialQueueTests(unittest.TestCase):
    def test_enqueue_is_transactional_and_idempotent_contract(self):
        connection = FakeConnection(rows=[("book-uuid", "PKP-UP-" + "a" * 32, "queued_for_analysis"), (73,)])
        result = enqueue_manuscript(
            lambda: connection, upload_id="PKP-UP-" + "a" * 32,
            source_sha256="b" * 64, original_filename="nia.md",
        )
        self.assertEqual(result["job_id"], 73)
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        self.assertTrue(connection.closed)
        statements = " ".join(call.args[0] for call in connection.cursor_obj.execute.call_args_list)
        self.assertIn("on conflict (source_sha256) do nothing", statements)
        self.assertIn("on conflict (book_id, job_type) do nothing", statements)

    def test_enqueue_rolls_back_on_reference_collision(self):
        connection = FakeConnection(rows=[("book-uuid", "PKP-UP-" + "c" * 32, "queued_for_analysis")])
        with self.assertRaises(PostgresEditorialQueueError):
            enqueue_manuscript(
                lambda: connection, upload_id="PKP-UP-" + "a" * 32,
                source_sha256="b" * 64, original_filename="nia.md",
            )
        self.assertEqual(connection.rollbacks, 1)

    def test_claim_uses_database_function_and_commits(self):
        connection = FakeConnection(rows=[(91, "queued")])
        result = claim_editorial_job(lambda: connection, worker_id="worker-01")
        self.assertEqual(result["job_id"], 91)
        self.assertIn("claim_editorial_job", connection.cursor_obj.execute.call_args.args[0])
        self.assertEqual(connection.commits, 1)

    def test_complete_rejects_stale_lease_and_rolls_back(self):
        connection = FakeConnection(rows=[None])
        with self.assertRaises(PostgresEditorialQueueError):
            complete_editorial_job(
                lambda: connection, job_id=91, worker_id="worker-01",
                result={"sections": 3}, book_status="analysis_ready",
            )
        self.assertEqual(connection.rollbacks, 1)

    def test_failure_records_retry_using_owned_lease(self):
        connection = FakeConnection(rows=[("queued", "book-uuid")])
        fail_editorial_job(
            lambda: connection, job_id=91, worker_id="worker-01",
            error="temporary error", retry_delay_seconds=10,
        )
        self.assertEqual(connection.commits, 1)

    def test_review_decision_is_idempotent_for_already_reviewed_asset(self):
        connection = FakeConnection(rows=[("book-uuid", 1, "approved")])
        from papi_core.papi_kids_postgres_queue import review_illustration_asset
        result = review_illustration_asset(
            lambda: connection, asset_id="PKP-ASSET-" + "a" * 24,
            decision="approved", reviewer_id="owner-01",
        )
        self.assertEqual(result["review_status"], "approved")
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.cursor_obj.execute.call_count, 1)

    def test_manuscript_safety_review_is_persisted_and_hash_bound(self):
        upload_id = "PKP-UP-" + "a" * 32
        digest = "b" * 64
        screening = {
            "manuscript_sha256": digest,
            "issue_count": 2,
            "critical_issue_count": 1,
        }
        connection = FakeConnection(rows=[("book-uuid", digest), (screening,)])
        result = record_manuscript_safety_review(
            lambda: connection, upload_id=upload_id, manuscript_sha256=digest,
            decision="approved", reviewer_id="owner-01",
            notes="Le passage dangereux a été réécrit et validé avec un adulte.",
        )
        self.assertTrue(result["approved"])
        self.assertEqual(result["manuscript_sha256"], digest)
        self.assertEqual(len(result["evidence_ref"]), 64)
        self.assertEqual(connection.commits, 1)
        statements = " ".join(call.args[0] for call in connection.cursor_obj.execute.call_args_list)
        self.assertIn("manuscript_safety_reviews", statements)
        self.assertIn("content_safety_review", statements)

    def test_safety_review_rejects_stale_hash_and_missing_resolution_notes(self):
        upload_id = "PKP-UP-" + "c" * 32
        connection = FakeConnection(rows=[("book-uuid", "b" * 64)])
        with self.assertRaises(PostgresEditorialQueueError):
            record_manuscript_safety_review(
                lambda: connection, upload_id=upload_id, manuscript_sha256="c" * 64,
                decision="approved", reviewer_id="owner-01", notes="Notes suffisantes pour approuver.",
            )
        self.assertEqual(connection.rollbacks, 1)

        connection = FakeConnection(rows=[("book-uuid", "b" * 64), ({
            "manuscript_sha256": "b" * 64, "issue_count": 1, "critical_issue_count": 1
        },)])
        with self.assertRaises(ValueError):
            record_manuscript_safety_review(
                lambda: connection, upload_id=upload_id, manuscript_sha256="b" * 64,
                decision="approved", reviewer_id="owner-01", notes="",
            )
        self.assertEqual(connection.rollbacks, 1)

    def test_kdp_listing_metadata_draft_is_versioned_and_persisted_even_when_incomplete(self):
        upload_id = "PKP-UP-" + "e" * 32
        connection = FakeConnection(rows=[("book-uuid",), (3,)])
        metadata = {
            "title": "Nia et la rivière aux mille reflets",
            "language": "fr",
        }
        result = record_kdp_listing_metadata(
            lambda: connection, upload_id=upload_id,
            metadata=metadata, editor_id="owner-01",
        )
        self.assertEqual(result["version"], 3)
        self.assertEqual(result["status"], "incomplete")
        self.assertGreater(result["blocker_count"], 0)
        self.assertEqual(len(result["metadata_sha256"]), 64)
        self.assertEqual(connection.commits, 1)
        statements = " ".join(call.args[0] for call in connection.cursor_obj.execute.call_args_list)
        self.assertIn("kdp_listing_metadata_versions", statements)
        self.assertIn("kdp_listing_metadata_status", statements)

    def test_kdp_listing_metadata_rejects_invalid_editor_identity_before_database(self):
        connection = FakeConnection()
        with self.assertRaises(ValueError):
            record_kdp_listing_metadata(
                lambda: connection, upload_id="PKP-UP-" + "f" * 32,
                metadata={"title": "Nia"}, editor_id="x",
            )
        self.assertEqual(connection.cursor_obj.execute.call_count, 0)

    def test_kdp_package_manifest_is_persisted_append_only(self):
        import hashlib
        import json
        upload_id = "PKP-UP-" + "f" * 32
        manifest = {
            "upload_id": upload_id, "package_version": 1,
            "pdfs": {"interior": {"page_count": 24}, "cover": {"page_count": 1}},
            "print_spec": {"trim_size": "8.5x8.5"},
        }
        canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        connection = FakeConnection(rows=[("book-uuid",)])
        result = record_kdp_package_build(
            lambda: connection, upload_id=upload_id,
            package_manifest=manifest, package_manifest_sha256=digest,
            build_status="generated_pending_manual_pdf_inspection",
        )
        self.assertEqual(result["package_version"], 1)
        self.assertEqual(result["manifest_sha256"], digest)
        self.assertEqual(connection.commits, 1)
        statements = " ".join(call.args[0] for call in connection.cursor_obj.execute.call_args_list)
        self.assertIn("kdp_package_builds", statements)
        self.assertIn("kdp_package_build", statements)

    def test_kdp_package_manifest_rejects_hash_mismatch_before_database(self):
        connection = FakeConnection()
        with self.assertRaises(ValueError):
            record_kdp_package_build(
                lambda: connection, upload_id="PKP-UP-" + "a" * 32,
                package_manifest={"upload_id": "PKP-UP-" + "a" * 32, "package_version": 1},
                package_manifest_sha256="0" * 64,
                build_status="generated_pending_manual_pdf_inspection",
            )
        self.assertEqual(connection.cursor_obj.execute.call_count, 0)

    def test_kdp_package_review_is_bound_to_latest_artifact_hash(self):
        upload_id = "PKP-UP-" + "1" * 32
        digest = "a" * 64
        manifest = {"pdfs": {"interior": {"sha256": digest}}}
        connection = FakeConnection(rows=[("book-uuid",), (1, manifest)])
        result = record_kdp_package_review(
            lambda: connection, upload_id=upload_id, artifact="interior",
            artifact_sha256=digest, decision="approved", reviewer_id="owner-01",
            notes="PDF inspecté page par page, marges et images contrôlées.",
        )
        self.assertTrue(result["approved"])
        self.assertEqual(result["artifact_sha256"], digest)
        self.assertEqual(len(result["evidence_ref"]), 64)
        self.assertEqual(connection.commits, 1)
        statements = " ".join(call.args[0] for call in connection.cursor_obj.execute.call_args_list)
        self.assertIn("kdp_package_reviews", statements)
        self.assertIn("kdp_package_reviews", statements)

    def test_kdp_package_review_rejects_stale_hash_and_short_notes(self):
        upload_id = "PKP-UP-" + "2" * 32
        connection = FakeConnection(rows=[("book-uuid",), (1, {"pdfs": {"cover": {"sha256": "a" * 64}}})])
        with self.assertRaises(PostgresEditorialQueueError):
            record_kdp_package_review(
                lambda: connection, upload_id=upload_id, artifact="cover",
                artifact_sha256="b" * 64, decision="approved", reviewer_id="owner-01",
                notes="Notes de revue suffisantes.",
            )
        self.assertEqual(connection.rollbacks, 1)
        connection = FakeConnection()
        with self.assertRaises(ValueError):
            record_kdp_package_review(
                lambda: connection, upload_id=upload_id, artifact="cover",
                artifact_sha256="a" * 64, decision="approved", reviewer_id="owner-01",
                notes="trop court",
            )
        self.assertEqual(connection.cursor_obj.execute.call_count, 0)

    def test_library_reader_returns_bounded_sanitized_book_summaries(self):
        connection = FakeConnection()
        connection.cursor_obj.fetchall.return_value = [
            ("PKP-UP-" + "a" * 32, "Nia", "queued_for_analysis", None, None,
             "queued", 0, 5, 24, 20)
        ]
        connection.cursor_obj.description = [
            ("upload_id",), ("display_title",), ("book_status",), ("created_at",),
            ("updated_at",), ("job_status",), ("attempts",), ("max_attempts",),
            ("illustration_count",), ("approved_illustration_count",),
        ]
        from papi_core.papi_kids_postgres_queue import build_postgres_library_reader
        books = build_postgres_library_reader(lambda: connection)()
        self.assertEqual(books[0]["title"], "Nia")
        self.assertEqual(books[0]["approved_illustration_count"], 20)
        self.assertNotIn("storage_key", books[0])
        self.assertEqual(connection.commits, 1)

    def test_status_reader_exposes_safety_screening_and_human_attestation(self):
        from papi_core.papi_kids_postgres_queue import build_postgres_status_reader
        upload_id = "PKP-UP-" + "d" * 32
        analysis = {"child_safety_screening": {"issue_count": 2, "critical_issue_count": 1}}
        review = {"approved": True, "reviewer_id": "owner-01", "manuscript_sha256": "b" * 64}
        connection = FakeConnection(rows=[(
            "book-uuid", upload_id, "needs_editor_review", None, None, review,
            {"title": "Nia"}, "incomplete", ["Auteur absent"],
            {"package_version": 1, "status": "generated_pending_manual_pdf_inspection"},
            {"v1:interior": {"approved": True}},
            71, "completed", 1, 5, None, None, analysis,
        )])
        connection.cursor_obj.description = [
            ("book_id",), ("upload_id",), ("book_status",), ("created_at",),
            ("updated_at",), ("content_safety_review",), ("kdp_listing_metadata",),
            ("kdp_listing_metadata_status",), ("kdp_listing_metadata_blockers",),
            ("kdp_package_build",), ("kdp_package_reviews",), ("job_id",),
            ("job_status",), ("attempts",), ("max_attempts",),
            ("available_at",), ("lease_until",), ("analysis",),
        ]
        connection.cursor_obj.fetchall.return_value = []
        result = build_postgres_status_reader(lambda: connection)(upload_id)
        self.assertEqual(result["job"]["analysis"]["child_safety_screening"]["issue_count"], 2)
        self.assertTrue(result["content_safety_review"]["approved"])
        self.assertEqual(result["kdp_listing_metadata"]["title"], "Nia")
        self.assertEqual(result["kdp_listing_metadata_status"], "incomplete")
        self.assertEqual(result["kdp_listing_metadata_blockers"], ["Auteur absent"])
        self.assertEqual(result["kdp_package_build"]["package_version"], 1)
        self.assertTrue(result["kdp_package_reviews"]["v1:interior"]["approved"])

    def test_invalid_identifiers_fail_before_database_access(self):
        with self.assertRaises(ValueError):
            enqueue_manuscript(
                lambda: self.fail("connection must not be opened"),
                upload_id="../bad", source_sha256="b" * 64, original_filename="x.md",
            )


if __name__ == "__main__":
    unittest.main()
