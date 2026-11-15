import unittest
from unittest.mock import Mock

from papi_core.papi_kids_postgres_queue import (
    PostgresEditorialQueueError,
    enqueue_manuscript,
    claim_editorial_job,
    complete_editorial_job,
    fail_editorial_job,
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

    def test_invalid_identifiers_fail_before_database_access(self):
        with self.assertRaises(ValueError):
            enqueue_manuscript(
                lambda: self.fail("connection must not be opened"),
                upload_id="../bad", source_sha256="b" * 64, original_filename="x.md",
            )


if __name__ == "__main__":
    unittest.main()
