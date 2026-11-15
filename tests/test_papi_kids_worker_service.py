import os
import sys
import types
import unittest
from unittest.mock import patch

from papi_core.papi_kids_worker_service import (
    PapiKidsWorkerConfigurationError,
    create_postgres_connection_factory,
    run_worker_loop,
)


class PapiKidsWorkerServiceTests(unittest.TestCase):
    def test_disabled_worker_does_not_claim_jobs_or_sleep(self):
        result = run_worker_loop(
            lambda: self.fail("database must not be opened"),
            storage_root="/private", worker_id="worker-01", enabled=False,
            sleep_fn=lambda _: self.fail("disabled worker must not sleep"),
        )
        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["provider_calls"], 0)

    def test_worker_processes_bounded_batches_and_sleeps_when_idle(self):
        outcomes = iter([
            {"status": "completed", "processed": True},
            {"status": "idle", "processed": False},
            {"status": "idle", "processed": False},
        ])
        sleeps = []
        with patch("papi_core.papi_kids_worker_service.run_one_editorial_job",
                   side_effect=lambda *args, **kwargs: next(outcomes)):
            result = run_worker_loop(
                lambda: None, storage_root="/private", worker_id="worker-01",
                enabled=True, max_jobs_per_cycle=3, max_cycles=2,
                idle_sleep_seconds=5, active_sleep_seconds=.25,
                sleep_fn=sleeps.append,
            )
        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["cycles"], 2)
        self.assertEqual(result["provider_calls"], 0)
        self.assertEqual(sleeps, [.25])

    def test_worker_stops_when_stop_requested(self):
        with patch("papi_core.papi_kids_worker_service.run_one_editorial_job") as run:
            result = run_worker_loop(
                lambda: None, storage_root="/private", worker_id="worker-01",
                enabled=True, stop_requested=lambda: True,
            )
        run.assert_not_called()
        self.assertEqual(result["cycles"], 0)

    def test_requires_tls_postgres_url(self):
        with patch.dict(os.environ, {"PAPI_KIDS_DATABASE_URL": "postgresql://user:pass@db.example.com:5432/db"}):
            with self.assertRaises(PapiKidsWorkerConfigurationError):
                create_postgres_connection_factory()

    def test_rejects_local_database_in_production(self):
        with patch.dict(os.environ, {
            "PAPI_KIDS_DATABASE_URL": "postgresql://user:pass@localhost:5432/db?sslmode=require"
        }):
            with self.assertRaises(PapiKidsWorkerConfigurationError):
                create_postgres_connection_factory()

    def test_connection_factory_uses_server_dsn_without_logging_it(self):
        fake = types.SimpleNamespace(connect=lambda dsn: ("connected", dsn))
        with patch.dict(os.environ, {
            "PAPI_KIDS_DATABASE_URL": "postgresql://user:secret@db.example.com:5432/db?sslmode=require"
        }), patch.dict(sys.modules, {"psycopg": fake}):
            factory = create_postgres_connection_factory()
            self.assertEqual(factory()[0], "connected")


if __name__ == "__main__":
    unittest.main()
