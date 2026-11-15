import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from papi_core.papi_kids_editorial_worker import run_one_editorial_job


class EditorialWorkerTests(unittest.TestCase):
    def test_idle_worker_does_not_process(self):
        with patch("papi_core.papi_kids_editorial_worker.claim_editorial_job", return_value=None):
            result = run_one_editorial_job(lambda: None, storage_root="/private", worker_id="worker-01")
        self.assertEqual(result, {"status": "idle", "processed": False})

    def test_worker_completes_offline_analysis_without_ai(self):
        upload_id = "PKP-UP-" + "a" * 32
        record = {"status": "analysis_ready", "analysis": {
            "ai_invoked": False, "provider_invoked": False, "section_count": 2
        }}
        with tempfile.TemporaryDirectory() as root:
            with patch("papi_core.papi_kids_editorial_worker.claim_editorial_job", return_value={
                "job_id": 17, "payload": {"upload_id": upload_id}
            }), patch("papi_core.papi_kids_editorial_worker.analyze_queued_manuscript", return_value=record), \
                 patch("papi_core.papi_kids_editorial_worker.complete_editorial_job") as complete:
                result = run_one_editorial_job(lambda: None, storage_root=root, worker_id="worker-01")
        self.assertEqual(result["status"], "completed")
        self.assertFalse(result["ai_invoked"])
        complete.assert_called_once()

    def test_worker_retries_on_local_analysis_error(self):
        with tempfile.TemporaryDirectory() as root:
            with patch("papi_core.papi_kids_editorial_worker.claim_editorial_job", return_value={
                "job_id": 18, "payload": {"upload_id": "PKP-UP-" + "b" * 32}
            }), patch("papi_core.papi_kids_editorial_worker.analyze_queued_manuscript", side_effect=OSError("missing")), \
                 patch("papi_core.papi_kids_editorial_worker.fail_editorial_job", return_value="queued") as fail:
                result = run_one_editorial_job(lambda: None, storage_root=root, worker_id="worker-02")
        self.assertEqual(result["status"], "queued")
        fail.assert_called_once()


if __name__ == "__main__":
    unittest.main()
