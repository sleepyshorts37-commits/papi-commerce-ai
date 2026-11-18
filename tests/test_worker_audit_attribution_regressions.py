"""Worker audit attribution regressions for attempt-scoped events."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from papi_core.audit import read_events
from papi_core.authz import AccessDenied, AuthenticatedAuthorizationDenied
from papi_core.execution_queue import ExecutionQueue
from papi_core.handler_registry import HandlerRegistry
from papi_core.storage import SupabaseStore
from papi_core.worker import PapiWorker


ATTEMPT_ID = "00000000-0000-4000-8000-000000000001"


class WorkerAuditAttributionRegressionTests(unittest.TestCase):
    def _worker(self, directory, *, handler_calls):
        queue = ExecutionQueue(SupabaseStore(
            url="https://example.supabase.co", key="test-key"
        ))
        registry = HandlerRegistry()
        registry.register(
            "internal.echo", "read_only",
            lambda payload, context: handler_calls.append(True) or {"ok": True},
        )
        worker = PapiWorker(
            queue=queue,
            registry=registry,
            policy={
                "execution_enabled": True,
                "external_actions_enabled": False,
                "allowed_handlers": ["internal.echo"],
                "action_permissions": {
                    "read_only": {"enabled": True, "owner_approval": False}
                },
            },
            worker_id="worker-attribution-test",
            audit_path=Path(directory) / "audit.jsonl",
        )
        job = {
            "id": "job-attribution",
            "task_id": "task-attribution",
            "handler": "internal.echo",
            "payload": {},
            "lease_token": "lease-attribution",
            "attempt_id": ATTEMPT_ID,
            "agent_identity": {"signed": "placeholder"},
        }
        task = {
            "id": "task-attribution",
            "owner_agent": "agent-authenticated",
            "status": "in_progress",
            "approval_required": False,
        }
        return worker, queue, job, task

    def _patch_queue(self, queue, job, task):
        return (
            patch.object(queue, "claim", return_value=job),
            patch.object(queue.store, "get_task", return_value={"task": task}),
            patch.object(queue, "fail", return_value="retry"),
        )

    def test_pre_authentication_failure_stays_attributed_to_system_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            handler_calls = []
            worker, queue, job, task = self._worker(directory, handler_calls=handler_calls)
            claim, get_task, fail = self._patch_queue(queue, job, task)
            with claim, get_task, fail as fail_mock, patch(
                "papi_core.worker.authorize_authenticated_agent",
                side_effect=AccessDenied("invalid signature"),
            ):
                result = worker.run_once()

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(fail_mock.call_args.kwargs["error_code"], "authentication_failed")
            events = read_events(worker.audit_path)
            blocked = next(e for e in events if e["action"] == "job.authentication_blocked")
            self.assertEqual(blocked["actor"], "system:worker:worker-attribution-test")
            self.assertIsNone(blocked["details"]["agent_id"])
            self.assertFalse(any(e["action"] == "job.handler_started" for e in events))
            self.assertEqual(handler_calls, [])

    def test_post_authentication_policy_failure_uses_verified_agent_and_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            handler_calls = []
            worker, queue, job, task = self._worker(directory, handler_calls=handler_calls)
            claim, get_task, fail = self._patch_queue(queue, job, task)
            principal = SimpleNamespace(agent_id="agent-authenticated")
            denial = AuthenticatedAuthorizationDenied(principal)
            with claim, get_task, fail as fail_mock, patch(
                "papi_core.worker.authorize_authenticated_agent",
                side_effect=denial,
            ):
                result = worker.run_once()

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(fail_mock.call_args.kwargs["error_code"], "permission_denied")
            events = read_events(worker.audit_path)
            blocked = next(e for e in events if e["action"] == "job.blocked")
            self.assertEqual(blocked["actor"], "agent-authenticated")
            self.assertEqual(blocked["details"]["agent_id"], "agent-authenticated")
            self.assertEqual(blocked["details"]["job_id"], "job-attribution")
            self.assertEqual(blocked["details"]["task_id"], "task-attribution")
            self.assertEqual(blocked["details"]["attempt_id"], ATTEMPT_ID)
            self.assertEqual(blocked["details"]["worker_id"], "worker-attribution-test")
            self.assertEqual(blocked["details"]["outcome"], "authenticated_agent_permission_denied")
            self.assertEqual(blocked["details"]["dedupe_id"], blocked["event_id"].removeprefix("worker:"))
            self.assertFalse(any(e["action"] == "job.handler_started" for e in events))
            self.assertEqual(handler_calls, [])


if __name__ == "__main__":
    unittest.main()
