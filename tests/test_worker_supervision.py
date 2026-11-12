import copy
import unittest

from papi_core.worker_supervision import WorkerSupervisionError, build_worker_supervision


class WorkerSupervisionTests(unittest.TestCase):
    def setUp(self):
        self.worker = {
            "worker_id": "agent-a", "status": "active",
            "last_heartbeat_at": "2026-11-12T10:00:00Z",
            "permissions": ["reports.build"],
            "identity": {"status": "active", "profile_state": "complete",
                         "permissions": ["reports.build"]},
        }

    def run_check(self, jobs=None, workers=None, **kwargs):
        return build_worker_supervision(jobs or [], workers or [self.worker],
            as_of="2026-11-12T10:01:00Z", **kwargs)

    def codes(self, result):
        return {item["code"] for item in result["issues"]}

    def test_healthy_worker_has_no_issue(self):
        result = self.run_check()
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["workers"][0]["heartbeat"], "healthy")

    def test_stale_heartbeat_is_critical(self):
        worker = copy.deepcopy(self.worker)
        worker["last_heartbeat_at"] = "2026-11-12T09:50:00Z"
        self.assertIn("heartbeat_stale", self.codes(self.run_check(workers=[worker])))

    def test_missing_heartbeat_is_unknown_not_dead(self):
        worker = copy.deepcopy(self.worker)
        worker.pop("last_heartbeat_at")
        result = self.run_check(workers=[worker])
        self.assertIn("heartbeat_unverified", self.codes(result))
        self.assertNotIn("worker_offline", self.codes(result))

    def test_offline_and_identity_mismatch_are_reported(self):
        worker = copy.deepcopy(self.worker)
        worker["status"] = "offline"
        worker["identity"]["permissions"] = ["other"]
        codes = self.codes(self.run_check(workers=[worker]))
        self.assertIn("worker_offline", codes)
        self.assertIn("identity_invalid_or_permissions_mismatch", codes)

    def test_expired_lease_is_reported_without_recovery(self):
        job = {"id": "J1", "status": "running", "lease_until": "2026-11-12T10:00:00Z"}
        result = self.run_check(jobs=[job])
        self.assertIn("lease_expired", self.codes(result))
        self.assertEqual(result["retries_triggered"], 0)

    def test_repeated_failures_and_exhaustion(self):
        repeated = {"id": "J1", "status": "retry", "attempts": 3, "max_attempts": 5}
        exhausted = {"id": "J2", "status": "failed", "attempts": 5, "max_attempts": 5}
        codes = self.codes(self.run_check(jobs=[repeated, exhausted]))
        self.assertIn("repeated_failures", codes)
        self.assertIn("retry_exhausted", codes)

    def test_invalid_timestamps_fail_closed(self):
        worker = copy.deepcopy(self.worker)
        worker["last_heartbeat_at"] = "yesterday"
        with self.assertRaises(WorkerSupervisionError):
            self.run_check(workers=[worker])

    def test_future_heartbeat_fails_closed(self):
        worker = copy.deepcopy(self.worker)
        worker["last_heartbeat_at"] = "2026-11-12T11:00:00Z"
        with self.assertRaises(WorkerSupervisionError):
            self.run_check(workers=[worker])

    def test_inputs_are_not_mutated(self):
        jobs, workers = [{"id": "J1", "status": "queued"}], [copy.deepcopy(self.worker)]
        before = copy.deepcopy((jobs, workers))
        self.run_check(jobs, workers)
        self.assertEqual((jobs, workers), before)

    def test_thresholds_must_be_positive(self):
        with self.assertRaises(WorkerSupervisionError):
            self.run_check(heartbeat_timeout_seconds=0)


if __name__ == "__main__":
    unittest.main()
