import unittest

from papi_core.worker_manager import WorkerManagerError, build_worker_plan


class WorkerManagerTests(unittest.TestCase):
    def setUp(self):
        self.policy = {"execution_enabled": False, "external_actions_enabled": False}
        self.handlers = {"report.build": {"permission": "reports.build", "enabled": True}}
        self.worker = {
            "worker_id": "agent-a", "status": "active",
            "permissions": ["reports.build"],
            "identity": {
                "status": "active", "profile_state": "complete",
                "permissions": ["reports.build"], "prohibited_actions": [],
            },
        }

    def test_disabled_policy_holds_eligible_job_without_claiming(self):
        result = build_worker_plan(
            [{"id": "J1", "status": "queued", "handler": "report.build"}],
            [self.worker], as_of="2026-11-12T10:00:00Z",
            handlers=self.handlers, policy=self.policy,
        )
        self.assertEqual(result["decisions"][0]["decision"], "hold")
        self.assertEqual(result["decisions"][0]["eligible_workers"], ["agent-a"])
        self.assertTrue(result["read_only"])
        self.assertEqual(result["handlers_executed"], 0)

    def test_unknown_handler_is_blocked(self):
        result = build_worker_plan(
            [{"id": "J1", "status": "queued", "handler": "shell.run"}],
            [self.worker], as_of="2026-11-12T10:00:00Z",
            handlers=self.handlers, policy=self.policy,
        )
        self.assertEqual(result["decisions"][0]["reason"], "handler_not_registered")

    def test_worker_requires_active_complete_identity_and_permission(self):
        worker = {**self.worker, "status": "planned"}
        result = build_worker_plan(
            [{"id": "J1", "status": "queued", "handler": "report.build"}],
            [worker], as_of="2026-11-12T10:00:00Z",
            handlers=self.handlers, policy=self.policy,
        )
        self.assertEqual(result["decisions"][0]["reason"], "no_eligible_worker")

    def test_active_lease_is_monitored(self):
        result = build_worker_plan(
            [{"id": "J1", "status": "running", "handler": "report.build",
              "lease_owner": "agent-a", "lease_until": "2026-11-12T10:01:00Z"}],
            [self.worker], as_of="2026-11-12T10:00:00Z",
            handlers=self.handlers, policy=self.policy,
        )
        self.assertEqual(result["decisions"][0]["decision"], "monitor")

    def test_expired_lease_is_reconsidered(self):
        result = build_worker_plan(
            [{"id": "J1", "status": "running", "handler": "report.build",
              "lease_owner": "agent-a", "lease_until": "2026-11-12T09:59:00Z"}],
            [self.worker], as_of="2026-11-12T10:00:00Z",
            handlers=self.handlers, policy=self.policy,
        )
        self.assertEqual(result["decisions"][0]["decision"], "hold")

    def test_duplicate_workers_and_naive_time_are_rejected(self):
        with self.assertRaises(WorkerManagerError):
            build_worker_plan([], [self.worker, self.worker],
                as_of="2026-11-12T10:00:00Z", handlers=self.handlers, policy=self.policy)
        with self.assertRaises(WorkerManagerError):
            build_worker_plan([], [], as_of="2026-11-12T10:00:00",
                handlers=self.handlers, policy=self.policy)


if __name__ == "__main__":
    unittest.main()
