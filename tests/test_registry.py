import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from papi_core.registry import load_agents, validate_task, validate_registries
from papi_core.audit import AuditError, append_event, new_event, read_events
from papi_core.orchestrator import build_dispatch_plan
from papi_core.state_machine import TransitionError, approve_task, transition_task
from papi_core.storage import StoreError, SupabaseStore


class RegistryTests(unittest.TestCase):
    def test_committed_registries_are_valid(self):
        self.assertEqual(validate_registries(), [])

    def test_registry_rejects_unknown_hierarchical_manager(self):
        with tempfile.TemporaryDirectory() as directory:
            agents_path = Path(directory) / "agents.json"
            tasks_path = Path(directory) / "tasks.json"
            agents_path.write_text(json.dumps({"agents": [
                {"id": "agent-a", "name": "Agent A", "manager_agent_id": "missing-manager"}
            ]}), encoding="utf-8")
            tasks_path.write_text(json.dumps({"tasks": []}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Responsable inconnu"):
                validate_registries(agents_path, tasks_path)

    def test_registry_rejects_case_insensitive_duplicate_agent_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            agents_path = Path(directory) / "agents.json"
            tasks_path = Path(directory) / "tasks.json"
            agents_path.write_text(json.dumps({"agents": [
                {"id": "agent-a", "name": "Agent A"},
                {"id": "AGENT-A", "name": "Agent A duplicate"}
            ]}), encoding="utf-8")
            tasks_path.write_text(json.dumps({"tasks": []}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "dupliqué ou réservé"):
                validate_registries(agents_path, tasks_path)

    def test_unknown_agent_is_rejected(self):
        task = {
            "id": "PAPI-TEST-001", "title": "Test", "department": "Test",
            "owner_agent": "agent-inexistant", "status": "backlog",
            "priority": "normal", "created_at": "2026-11-11T00:00:00Z",
            "approval_required": False
        }
        errors = validate_task(task, load_agents())
        self.assertTrue(any("Agent inconnu" in error for error in errors))

    def test_unapproved_task_cannot_start(self):
        task = {
            "id": "PAPI-TEST-002", "title": "Test", "department": "Test",
            "owner_agent": "astou", "status": "in_progress",
            "priority": "normal", "created_at": "2026-11-11T00:00:00Z",
            "approval_required": True, "approval_status": "pending"
        }
        errors = validate_task(task, load_agents())
        self.assertTrue(any("sans approbation" in error for error in errors))

    def test_done_task_requires_evidence(self):
        task = {
            "id": "PAPI-TEST-003", "title": "Test", "department": "Test",
            "owner_agent": "astou", "status": "done", "priority": "normal",
            "created_at": "2026-11-11T00:00:00Z", "approval_required": False
        }
        errors = validate_task(task, load_agents())
        self.assertTrue(any("preuve" in error for error in errors))

    def test_dispatch_plan_is_proposal_only_and_priority_sorted(self):
        with tempfile.TemporaryDirectory() as directory:
            tasks_path = Path(directory) / "tasks.json"
            tasks_path.write_text(json.dumps({"tasks": [
                {"id": "PAPI-LOW-001", "department": "Prospection", "status": "ready", "priority": "low", "created_at": "2026-11-11"},
                {"id": "PAPI-HIGH-001", "department": "Prospection", "status": "ready", "priority": "high", "created_at": "2026-11-11"}
            ]}), encoding="utf-8")
            plan = build_dispatch_plan(tasks_path)
        self.assertEqual(plan["mode"], "proposal_only")
        self.assertEqual(plan["proposals"][0]["task_id"], "PAPI-HIGH-001")
        self.assertFalse(plan["proposals"][0]["dispatch_allowed"])
        self.assertEqual(plan["proposals"][0]["blocking_reason"], "no_deployed_agent")

    def test_approval_blocks_dispatch_proposal(self):
        with tempfile.TemporaryDirectory() as directory:
            tasks_path = Path(directory) / "tasks.json"
            tasks_path.write_text(json.dumps({"tasks": [
                {"id": "PAPI-APP-001", "department": "Direction", "status": "ready", "priority": "urgent", "approval_required": True, "approval_status": "pending"}
            ]}), encoding="utf-8")
            plan = build_dispatch_plan(tasks_path)
        self.assertEqual(plan["proposals"][0]["blocking_reason"], "approval_required")
        self.assertFalse(plan["proposals"][0]["dispatch_allowed"])


class AuditTests(unittest.TestCase):
    def make_event(self, event_id="EVT-001", details=None):
        return new_event(
            event_id=event_id, actor="astou", action="task.reviewed",
            entity_type="task", entity_id="PAPI-001", details=details or {"decision": "review"}
        )

    def test_append_and_read_audit_event(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            event = self.make_event()
            self.assertTrue(append_event(event, path))
            self.assertEqual(read_events(path), [event])

    def test_duplicate_event_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            event = self.make_event()
            self.assertTrue(append_event(event, path))
            self.assertFalse(append_event(event, path))
            self.assertEqual(len(read_events(path)), 1)

    def test_sensitive_fields_are_rejected(self):
        with self.assertRaises(AuditError):
            self.make_event(details={"access_token": "never-store"})

    def test_corrupt_log_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_text("{broken json}\n", encoding="utf-8")
            with self.assertRaises(AuditError):
                read_events(path)


class StateMachineTests(unittest.TestCase):
    def base_task(self, **changes):
        task = {
            "id": "PAPI-STATE-001", "status": "backlog",
            "approval_required": False, "evidence": []
        }
        task.update(changes)
        return task

    def test_valid_lifecycle_requires_quality_review_and_evidence(self):
        task, event1 = transition_task(self.base_task(), "ready", actor="marietou")
        task, event2 = transition_task(task, "in_progress", actor="astou")
        task, event3 = transition_task(task, "review", actor="astou")
        with self.assertRaises(TransitionError):
            transition_task(task, "done", actor="mariama")
        task, event4 = transition_task(task, "done", actor="mariama", evidence=["https://example.org/result"])
        self.assertEqual(task["status"], "done")
        self.assertEqual(event4["details"]["from_status"], "review")
        self.assertEqual(len({event1["event_id"], event2["event_id"], event3["event_id"], event4["event_id"]}), 4)

    def test_invalid_transition_is_rejected(self):
        with self.assertRaises(TransitionError):
            transition_task(self.base_task(), "done", actor="astou")

    def test_approval_is_required_before_execution(self):
        task = self.base_task(approval_required=True, approval_status="pending")
        task, _ = transition_task(task, "ready", actor="marietou")
        with self.assertRaises(TransitionError):
            transition_task(task, "in_progress", actor="astou")
        task, event = approve_task(task, approver="owner", decision="approved")
        task, _ = transition_task(task, "in_progress", actor="astou")
        self.assertEqual(task["status"], "in_progress")
        self.assertEqual(task["approval_status"], "approved")

    def test_approval_decision_cannot_be_overwritten(self):
        task = self.base_task(approval_required=True, approval_status="pending")
        task, _ = approve_task(task, approver="owner", decision="rejected")
        with self.assertRaises(TransitionError):
            approve_task(task, approver="owner", decision="approved")

    def test_cancelled_task_is_terminal(self):
        task, _ = transition_task(self.base_task(), "cancelled", actor="owner")
        with self.assertRaises(TransitionError):
            transition_task(task, "ready", actor="owner")


import unittest
from unittest.mock import patch

from papi_core.storage import StoreError, SupabaseStore


class StorageTests(unittest.TestCase):
    def test_requires_https_and_key(self):
        with self.assertRaises(StoreError):
            SupabaseStore(url="http://example.org", key="x")
        with self.assertRaises(StoreError):
            SupabaseStore(url="https://example.org", key="")

    @patch.dict("os.environ", {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_KEY": "test-key"})
    def test_task_insert_returns_version(self):
        store = SupabaseStore()
        with patch.object(store, "_request", return_value=[{"version": 1}]) as request:
            version = store.save_task({"id": "PAPI-001", "status": "backlog"})
        self.assertEqual(version, 1)
        self.assertEqual(request.call_args.args[0], "POST")

    @patch.dict("os.environ", {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_KEY": "test-key"})
    def test_task_update_uses_optimistic_version(self):
        store = SupabaseStore()
        with patch.object(store, "_request", return_value=[{"version": 3}]) as request:
            version = store.save_task({"id": "PAPI-001", "status": "ready"}, expected_version=2)
        self.assertEqual(version, 3)
        self.assertIn("version=eq.2", request.call_args.args[1])

    @patch.dict("os.environ", {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_KEY": "test-key"})
    def test_concurrent_update_conflict_is_rejected(self):
        store = SupabaseStore()
        with patch.object(store, "_request", return_value=[]):
            with self.assertRaises(StoreError):
                store.save_task({"id": "PAPI-001"}, expected_version=1)


    @patch.dict("os.environ", {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_KEY": "test-key"})
    def test_transition_and_audit_use_atomic_rpc(self):
        store = SupabaseStore()
        task = {"id": "PAPI-ATOMIC-001", "status": "backlog", "approval_required": False, "evidence": []}
        with patch.object(store, "_request", side_effect=[
            [{"task": task, "version": 4}],
            5,
        ]) as request:
            updated, version = store.transition_and_save(
                "PAPI-ATOMIC-001", "ready", actor="marietou", expected_version=4
            )
        self.assertEqual(updated["status"], "ready")
        self.assertEqual(version, 5)
        self.assertEqual(request.call_args_list[1].args[1], "rpc/papi_commit_task_change")
        payload = request.call_args_list[1].args[2]
        self.assertEqual(payload["p_expected_version"], 4)
        self.assertEqual(payload["p_event"]["entity_id"], "PAPI-ATOMIC-001")

    @patch.dict("os.environ", {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_KEY": "test-key"})
    def test_transition_refuses_stale_version_before_rpc(self):
        store = SupabaseStore()
        with patch.object(store, "_request", return_value=[{"task": {"id": "PAPI-001", "status": "backlog"}, "version": 2}]) as request:
            with self.assertRaises(StoreError):
                store.transition_and_save("PAPI-001", "ready", actor="astou", expected_version=1)
        request.assert_called_once()



class ExecutionQueueTests(unittest.TestCase):
    @patch.dict("os.environ", {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_KEY": "test-key"})
    def test_enqueue_uses_idempotency_key(self):
        from papi_core.execution_queue import ExecutionQueue
        queue = ExecutionQueue(SupabaseStore())
        with patch.object(queue.store, "_request", return_value=[{"id": "JOB-1"}]) as request:
            result = queue.enqueue(job_id="JOB-1", task_id="PAPI-1", handler="report.generate",
                                   payload={"format": "pdf"}, idempotency_key="PAPI-1:report:v1")
        self.assertEqual(result["id"], "JOB-1")
        self.assertEqual(request.call_args.args[1], "papi_jobs")
        self.assertEqual(request.call_args.args[2]["idempotency_key"], "PAPI-1:report:v1")

    @patch.dict("os.environ", {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_KEY": "test-key"})
    def test_claim_returns_none_when_queue_empty(self):
        from papi_core.execution_queue import ExecutionQueue
        queue = ExecutionQueue(SupabaseStore())
        with patch.object(queue.store, "_request", return_value=None):
            self.assertIsNone(queue.claim(worker_id="worker-01"))

    @patch.dict("os.environ", {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_KEY": "test-key"})
    def test_claim_rejects_invalid_lease_duration(self):
        from papi_core.execution_queue import ExecutionQueue, QueueError
        queue = ExecutionQueue(SupabaseStore())
        with self.assertRaises(QueueError):
            queue.claim(worker_id="worker-01", lease_seconds=5)

    @patch.dict("os.environ", {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_KEY": "test-key"})
    def test_complete_requires_current_lease(self):
        from papi_core.execution_queue import ExecutionQueue
        queue = ExecutionQueue(SupabaseStore())
        with patch.object(queue.store, "_request", return_value=False):
            self.assertFalse(queue.complete(job_id="JOB-1", worker_id="worker-01",
                                            lease_token="lease", result={"ok": True}))

    @patch.dict("os.environ", {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_KEY": "test-key"})
    def test_failure_result_is_retry_or_terminal(self):
        from papi_core.execution_queue import ExecutionQueue
        queue = ExecutionQueue(SupabaseStore())
        with patch.object(queue.store, "_request", return_value="retry"):
            self.assertEqual(queue.fail(job_id="JOB-1", worker_id="worker-01",
                                        lease_token="lease", error_code="temporary_failure"), "retry")


if __name__ == "__main__":
    unittest.main()


class HandlerPermissionTests(unittest.TestCase):
    def setUp(self):
        from papi_core.handler_registry import HandlerRegistry
        self.registry = HandlerRegistry()
        self.registry.register("internal.echo", "read_only", lambda payload, context: {"ok": True})
        self.policy = {
            "execution_enabled": True, "external_actions_enabled": False,
            "allowed_handlers": ["internal.echo"],
            "action_permissions": {"read_only": {"enabled": True, "owner_approval": False}},
        }
        self.job = {"handler": "internal.echo", "payload": {"hello": "world"}}
        self.task = {"status": "in_progress", "approval_required": False}

    def test_registered_and_allowed_handler_executes(self):
        from papi_core.handler_registry import execute_authorized_job
        result = execute_authorized_job(self.job, self.task, self.policy, self.registry)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["result"], {"ok": True})

    def test_execution_disabled_is_rejected(self):
        from papi_core.handler_registry import PermissionError, execute_authorized_job
        self.policy["execution_enabled"] = False
        with self.assertRaises(PermissionError):
            execute_authorized_job(self.job, self.task, self.policy, self.registry)

    def test_unknown_handler_is_rejected(self):
        from papi_core.handler_registry import PermissionError, authorize_job
        self.job["handler"] = "python.eval"
        with self.assertRaises(PermissionError):
            authorize_job(self.job, self.task, self.policy, self.registry)

    def test_handler_must_be_allowlisted_by_policy(self):
        from papi_core.handler_registry import PermissionError, authorize_job
        self.policy["allowed_handlers"] = []
        with self.assertRaises(PermissionError):
            authorize_job(self.job, self.task, self.policy, self.registry)

    def test_task_must_be_running_and_approved(self):
        from papi_core.handler_registry import PermissionError, authorize_job
        self.task["status"] = "ready"
        with self.assertRaises(PermissionError):
            authorize_job(self.job, self.task, self.policy, self.registry)
        self.task.update(status="in_progress", approval_required=True, approval_status="pending")
        with self.assertRaises(PermissionError):
            authorize_job(self.job, self.task, self.policy, self.registry)

    def test_external_action_is_blocked(self):
        from papi_core.handler_registry import HandlerRegistry, PermissionError, authorize_job
        registry = HandlerRegistry()
        registry.register("mail.send", "external_communication", lambda payload, context: {"sent": True})
        job = {"handler": "mail.send", "payload": {}}
        policy = {
            "execution_enabled": True, "external_actions_enabled": False,
            "allowed_handlers": ["mail.send"],
            "action_permissions": {"external_communication": {"enabled": True, "owner_approval": True}},
        }
        task = {"status": "in_progress", "approval_required": True, "approval_status": "approved"}
        with self.assertRaises(PermissionError):
            authorize_job(job, task, policy, registry)

    def test_non_object_handler_result_is_rejected(self):
        from papi_core.handler_registry import HandlerRegistry, PermissionError, execute_authorized_job
        registry = HandlerRegistry()
        registry.register("internal.bad", "read_only", lambda payload, context: "bad")
        policy = dict(self.policy, allowed_handlers=["internal.bad"])
        job = {"handler": "internal.bad", "payload": {}}
        with self.assertRaises(PermissionError):
            execute_authorized_job(job, self.task, policy, registry)


class WorkerTests(unittest.TestCase):
    def make_worker(self, policy=None, job=None, task=None):
        identity_patch = patch('papi_core.worker.authorize_authenticated_agent')
        identity_patch.start()
        self.addCleanup(identity_patch.stop)
        from papi_core.execution_queue import ExecutionQueue
        from papi_core.handler_registry import HandlerRegistry
        from papi_core.worker import PapiWorker
        queue = ExecutionQueue(SupabaseStore(url="https://example.supabase.co", key="test-key"))
        registry = HandlerRegistry()
        registry.register("internal.echo", "read_only", lambda payload, context: {"echo": payload})
        effective_policy = policy or {
            "execution_enabled": True, "external_actions_enabled": False,
            "allowed_handlers": ["internal.echo"],
            "action_permissions": {"read_only": {"enabled": True, "owner_approval": False}},
        }
        return PapiWorker(queue=queue, registry=registry, policy=effective_policy, worker_id="worker-test")

    def test_disabled_worker_does_not_claim(self):
        worker = self.make_worker(policy={"execution_enabled": False})
        with patch.object(worker.queue, "claim") as claim:
            self.assertEqual(worker.run_once(), {"status": "disabled", "claimed": False})
        claim.assert_not_called()

    def test_idle_worker_claims_nothing(self):
        worker = self.make_worker()
        with patch.object(worker.queue, "claim", return_value=None):
            self.assertEqual(worker.run_once(), {"status": "idle", "claimed": False})

    def test_worker_executes_one_authorized_job(self):
        worker = self.make_worker()
        job = {"id": "JOB-1", "task_id": "TASK-1", "handler": "internal.echo",
               "payload": {"a": 1}, "lease_token": "lease-1"}
        with patch.object(worker.queue, "claim", return_value=job), \
             patch.object(worker.queue.store, "get_task", return_value={
                 "task": {"status": "in_progress", "approval_required": False}
             }), \
             patch.object(worker.queue, "complete", return_value=True) as complete:
            result = worker.run_once()
        self.assertEqual(result["status"], "completed")
        complete.assert_called_once()

    def test_worker_blocks_unknown_handler_and_releases_job_to_retry(self):
        worker = self.make_worker()
        job = {"id": "JOB-2", "task_id": "TASK-1", "handler": "not.registered",
               "payload": {}, "lease_token": "lease-2"}
        with patch.object(worker.queue, "claim", return_value=job), \
             patch.object(worker.queue.store, "get_task", return_value={
                 "task": {"status": "in_progress", "approval_required": False}
             }), \
             patch.object(worker.queue, "fail", return_value="retry") as fail:
            result = worker.run_once()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(fail.call_args.kwargs["error_code"], "permission_denied")

    def test_worker_does_not_complete_if_lease_was_lost(self):
        worker = self.make_worker()
        job = {"id": "JOB-3", "task_id": "TASK-1", "handler": "internal.echo",
               "payload": {}, "lease_token": "lease-3"}
        with patch.object(worker.queue, "claim", return_value=job), \
             patch.object(worker.queue.store, "get_task", return_value={
                 "task": {"status": "in_progress", "approval_required": False}
             }), \
             patch.object(worker.queue, "complete", return_value=False):
            result = worker.run_once()
        self.assertEqual(result["status"], "lease_lost")


class DoctorTests(unittest.TestCase):
    def test_missing_environment_is_reported_without_secrets(self):
        from papi_core.doctor import diagnose_environment
        result = diagnose_environment({})
        self.assertEqual(result["status"], "configuration_incomplete")
        self.assertFalse(result["network_test_performed"])
        self.assertFalse(result["secrets_displayed"])
        self.assertFalse(result["worker_start_allowed"])

    def test_valid_shaped_environment_is_not_claimed_as_connected(self):
        from papi_core.doctor import diagnose_environment
        result = diagnose_environment({
            "SUPABASE_URL": "https://project.supabase.co",
            "SUPABASE_KEY": "dummy-secret-value",
        })
        self.assertEqual(result["status"], "configuration_present")
        self.assertTrue(result["checks"]["supabase_url_configured"])
        self.assertTrue(result["checks"]["supabase_key_configured"])
        self.assertFalse(result["network_test_performed"])
        self.assertNotIn("dummy-secret-value", json.dumps(result))

    def test_non_https_url_is_rejected(self):
        from papi_core.doctor import diagnose_environment
        result = diagnose_environment({
            "SUPABASE_URL": "http://project.supabase.co",
            "SUPABASE_KEY": "dummy",
        })
        self.assertFalse(result["checks"]["supabase_url_configured"])
    def test_failure_rejects_non_identifier_error_codes(self):
        from papi_core.execution_queue import ExecutionQueue, QueueError
        queue = ExecutionQueue(SupabaseStore(url="https://example.supabase.co", key="test-key"))
        with self.assertRaises(QueueError):
            queue.fail(job_id="JOB-1", worker_id="worker-01",
                       lease_token="lease", error_code="Bearer secret-value")

