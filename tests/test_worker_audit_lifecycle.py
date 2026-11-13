"""Lifecycle regression tests for worker audit attribution."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from papi_core.audit import read_events
from papi_core.execution_queue import ExecutionQueue
from papi_core.handler_registry import HandlerRegistry
from papi_core.storage import SupabaseStore
from papi_core.worker import PapiWorker


class WorkerAuditLifecycleTests(unittest.TestCase):
    def test_lost_lease_is_system_attributed_and_never_completed(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = ExecutionQueue(SupabaseStore(
                url="https://example.supabase.co", key="test-key"
            ))
            registry = HandlerRegistry()
            registry.register("internal.echo", "read_only",
                              lambda payload, context: {"ok": True})
            worker = PapiWorker(
                queue=queue, registry=registry,
                policy={
                    "execution_enabled": True,
                    "external_actions_enabled": False,
                    "allowed_handlers": ["internal.echo"],
                    "action_permissions": {
                        "read_only": {"enabled": True, "owner_approval": False}
                    },
                },
                worker_id="worker-lease-test",
                audit_path=Path(directory) / "audit.jsonl",
            )
            job = {
                "id": "JOB-LOST-LEASE",
                "task_id": "TASK-LOST-LEASE",
                "handler": "internal.echo",
                "payload": {"safe": True},
                "lease_token": "lease-token",
                "attempts": 1, "max_attempts": 5,
            }
            with patch("papi_core.worker.authorize_authenticated_agent",
                       return_value={"principal": SimpleNamespace(agent_id="agent-test")}), \
                 patch.object(queue, "claim", return_value=job), \
                 patch.object(queue.store, "get_task", return_value={
                     "task": {
                         "status": "in_progress",
                         "approval_required": False,
                         "owner_agent": "agent-test",
                     }
                 }), \
                 patch.object(queue, "renew", return_value=True), \
                 patch.object(queue, "complete", return_value=False) as complete, \
                 patch("papi_core.worker.execute_authorized_job",
                       return_value={"status": "completed"}):
                result = worker.run_once()

            self.assertEqual(result["status"], "lease_lost")
            complete.assert_called_once()
            events = read_events(worker.audit_path)
            lost = next(event for event in events
                        if event["action"] == "job.lease_lost")
            self.assertEqual(lost["actor"], "system:worker:worker-lease-test")
            self.assertFalse(any(event["action"] == "job.completed"
                                 for event in events))


if __name__ == "__main__":
    unittest.main()
