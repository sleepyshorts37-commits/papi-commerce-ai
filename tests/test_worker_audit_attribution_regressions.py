"""Regression tests for worker audit actor attribution and fail-closed startup."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from papi_core.audit import read_events
from papi_core.authz import AccessDenied
from papi_core.execution_queue import ExecutionQueue
from papi_core.handler_registry import HandlerRegistry, PermissionError as HandlerPermissionError
from papi_core.storage import SupabaseStore
from papi_core.worker import PapiWorker


class WorkerAuditAttributionRegressionTests(unittest.TestCase):
    def _worker(self, directory, *, handler=None):
        queue = ExecutionQueue(SupabaseStore(
            url="https://example.supabase.co", key="test-key"
        ))
        registry = HandlerRegistry()
        registry.register(
            "internal.echo", "read_only",
            handler or (lambda payload, context: {"ok": True}),
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
            "agent_identity": {"signed": "placeholder"},
        }
        task = {
            "id": "task-attribution",
            "owner_agent": "agent-authenticated",
            "status": "in_progress",
            "approval_required": False,
        }
        return worker, queue, job, task

    def _patch_inputs(self, queue, job, task):
        return (
            patch.object(queue, "claim", return_value=job),
            patch.object(queue.store, "get_task", return_value={"task": task}),
            patch.object(queue, "fail", return_value=True),
        )

    def test_authentication_failure_is_attributed_to_system_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            worker, queue, job, task = self._worker(directory)
            claim, get_task, fail = self._patch_inputs(queue, job, task)
            with claim, get_task, fail as fail_mock, \
                 patch("papi_core.worker.authorize_authenticated_agent",
                       side_effect=AccessDenied("invalid identity")):
                result = worker.run_once()

            self.assertEqual(result["status"], "blocked")
            events = read_events(worker.audit_path)
            blocked = next(e for e in events if e["action"] == "job.authentication_blocked")
            self.assertEqual(blocked["actor"], "system:worker:worker-attribution-test")
            self.assertFalse(any(e["action"] == "job.handler_started" for e in events))

    def test_post_authentication_policy_block_uses_authenticated_principal(self):
        with tempfile.TemporaryDirectory() as directory:
            worker, queue, job, task = self._worker(directory)
            claim, get_task, fail = self._patch_inputs(queue, job, task)
            principal = SimpleNamespace(agent_id="agent-authenticated")
            with claim, get_task, fail as fail_mock, \
                 patch("papi_core.worker.authorize_authenticated_agent",
                       return_value={"principal": principal}), \
                 patch("papi_core.worker.authorize_job",
                       side_effect=HandlerPermissionError("policy denied")):
                result = worker.run_once()

            self.assertEqual(result["status"], "blocked")
            events = read_events(worker.audit_path)
            blocked = next(e for e in events if e["action"] == "job.blocked")
            self.assertEqual(blocked["actor"], "agent-authenticated")
            self.assertFalse(any(e["action"] == "job.handler_started" for e in events))

    def test_handler_is_not_invoked_when_handler_started_audit_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            invoked = []
            worker, queue, job, task = self._worker(
                directory, handler=lambda payload, context: invoked.append(True)
            )
            claim, get_task, fail = self._patch_inputs(queue, job, task)
            principal = SimpleNamespace(agent_id="agent-authenticated")
            real_append = __import__("papi_core.worker", fromlist=["append_event"]).append_event

            def fail_handler_started(event, path):
                if event["action"] == "job.handler_started":
                    raise OSError("audit storage unavailable")
                return real_append(event, path)

            with claim, get_task, fail as fail_mock, \
                 patch.object(queue, "renew", return_value=True), \
                 patch("papi_core.worker.authorize_authenticated_agent",
                       return_value={"principal": principal}), \
                 patch("papi_core.worker.append_event", side_effect=fail_handler_started):
                result = worker.run_once()

            self.assertEqual(result["status"], "audit_blocked")
            self.assertEqual(invoked, [])
            self.assertEqual(fail_mock.call_count, 1)
            self.assertEqual(fail_mock.call_args.kwargs["error_code"], "audit_unavailable")


if __name__ == "__main__":
    unittest.main()
