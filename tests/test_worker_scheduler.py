import copy
import unittest

from papi_core.worker_scheduler import WorkerSchedulerError, build_schedule


class WorkerSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.policy = {"execution_enabled": False, "external_actions_enabled": False}
        self.handlers = {"report.build": {"permission": "reports.build", "enabled": True}}
        self.worker_a = {
            "worker_id": "agent-a", "status": "active", "capacity": 2,
            "permissions": ["reports.build"],
            "identity": {"status": "active", "profile_state": "complete",
                         "permissions": ["reports.build"], "prohibited_actions": []},
        }
        self.worker_b = copy.deepcopy(self.worker_a)
        self.worker_b["worker_id"] = "agent-b"

    def job(self, job_id, priority="normal", queued_at="2026-11-12T09:00:00Z"):
        return {"id": job_id, "status": "queued", "handler": "report.build",
                "priority": priority, "queued_at": queued_at}

    def schedule(self, jobs, workers=None, **kwargs):
        return build_schedule(jobs, workers or [self.worker_a, self.worker_b],
            as_of="2026-11-12T10:00:00Z", handlers=self.handlers,
            policy=self.policy, **kwargs)

    def test_policy_disabled_holds_all_candidates_read_only(self):
        result = self.schedule([self.job("J1")])
        self.assertEqual(result["schedule"], [])
        self.assertEqual(result["decisions"][0]["reason"], "execution_disabled")
        self.assertTrue(result["summary"]["read_only"])
        self.assertEqual(result["summary"]["claims_performed"], 0)

    def test_priority_and_aging_order_are_deterministic(self):
        result = self.schedule([
            self.job("low-old", "low", "2026-11-12T06:00:00Z"),
            self.job("urgent-new", "urgent", "2026-11-12T09:59:00Z"),
            self.job("high-new", "high", "2026-11-12T09:59:00Z"),
        ])
        ranks = [d["job_id"] for d in result["decisions"]]
        self.assertEqual(ranks, ["urgent-new", "low-old", "high-new"])

    def test_balances_workers_and_respects_capacity(self):
        policy = {"execution_enabled": True, "external_actions_enabled": False}
        result = build_schedule([self.job("J1"), self.job("J2"), self.job("J3")],
            [self.worker_a, self.worker_b], as_of="2026-11-12T10:00:00Z",
            handlers=self.handlers, policy=policy)
        self.assertEqual([x["worker_id"] for x in result["schedule"]],
                         ["agent-a", "agent-b", "agent-a"])
        self.assertEqual(result["summary"]["dispatch_candidates"], 3)

    def test_permission_parity_is_required(self):
        worker = copy.deepcopy(self.worker_a)
        worker["identity"]["permissions"] = ["other"]
        result = self.schedule([self.job("J1")], [worker])
        self.assertEqual(result["decisions"][0]["reason"], "no_eligible_worker")

    def test_unknown_handler_is_blocked(self):
        job = self.job("J1")
        job["handler"] = "shell.run"
        result = self.schedule([job])
        self.assertEqual(result["decisions"][0]["reason"], "handler_not_registered")

    def test_cycle_limit_defers_excess_jobs(self):
        policy = {"execution_enabled": True, "external_actions_enabled": False}
        result = build_schedule([self.job("J1"), self.job("J2")],
            [self.worker_a], as_of="2026-11-12T10:00:00Z",
            handlers=self.handlers, policy=policy, max_dispatch_per_cycle=1)
        self.assertEqual(len(result["schedule"]), 1)
        self.assertEqual(result["decisions"][1]["reason"], "cycle_limit_reached")

    def test_inputs_are_not_mutated(self):
        jobs = [self.job("J1")]
        workers = [copy.deepcopy(self.worker_a)]
        before = copy.deepcopy((jobs, workers))
        self.schedule(jobs, workers)
        self.assertEqual((jobs, workers), before)

    def test_invalid_timestamp_fails_closed(self):
        with self.assertRaises(WorkerSchedulerError):
            self.schedule([self.job("J1", queued_at="tomorrow")])

    def test_expired_running_lease_is_not_reclaimed_by_planner(self):
        job = {"id": "J1", "status": "running", "handler": "report.build",
               "lease_until": "2026-11-12T09:00:00Z", "lease_owner": "agent-a"}
        result = self.schedule([job])
        self.assertEqual(result["decisions"][0]["reason"],
                         "expired_lease_requires_recovery")


if __name__ == "__main__":
    unittest.main()
