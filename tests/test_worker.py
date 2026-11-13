import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from papi_core.handler_registry import HandlerRegistry
from papi_core.worker import PapiWorker, WorkerError


class QueueSpy:
    def __init__(self, claim_result=None):
        self.claim_result = claim_result
        self.claim_calls = 0
        self.fail_calls = []

    def claim(self, *, worker_id):
        self.claim_calls += 1
        return self.claim_result

    def fail(self, **kwargs):
        self.fail_calls.append(kwargs)
        return "failed"

    def complete(self, **kwargs):
        raise AssertionError("Un job non authentifié ne doit jamais être complété.")


class FakeStore:
    def get_task(self, task_id):
        return {"task": {"id": task_id, "owner_agent": "agent-a", "status": "in_progress",
                         "approval_required": False}}


class WorkerSafetyTests(unittest.TestCase):
    def test_disabled_worker_does_not_claim_a_job(self):
        queue = QueueSpy()
        worker = PapiWorker(queue=queue, registry=HandlerRegistry(),
            policy={"execution_enabled": False}, worker_id="worker-test")
        result = worker.run_once()
        self.assertEqual(result, {"status": "disabled", "claimed": False})
        self.assertEqual(queue.claim_calls, 0)

    def test_enabled_worker_with_empty_queue_returns_idle(self):
        queue = QueueSpy()
        worker = PapiWorker(queue=queue, registry=HandlerRegistry(),
            policy={"execution_enabled": True}, worker_id="worker-test")
        result = worker.run_once()
        self.assertEqual(result, {"status": "idle", "claimed": False})
        self.assertEqual(queue.claim_calls, 1)

    def test_blank_worker_id_is_rejected(self):
        with self.assertRaises(WorkerError):
            PapiWorker(queue=QueueSpy(), registry=HandlerRegistry(),
                policy={"execution_enabled": False}, worker_id=" ")

    def test_worker_blocks_job_without_signed_agent_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            job = {"id": "job-1", "task_id": "task-1", "handler": "report.preview",
                   "payload": {}, "lease_token": "lease-1", "attempts": 1, "max_attempts": 5, "agent_identity": None}
            queue = QueueSpy(job)
            queue.store = FakeStore()
            registry = HandlerRegistry()
            registry.register("report.preview", "read_only", lambda payload, context: {"ok": True})
            policy = {"execution_enabled": True, "allowed_handlers": ["report.preview"],
                      "action_permissions": {"read_only": {"enabled": True, "owner_approval": False}},
                      "external_actions_enabled": False}
            worker = PapiWorker(queue=queue, registry=registry, policy=policy,
                worker_id="worker-test", key_dir=Path(tmp) / "keys",
                replay_db=Path(tmp) / "replay.sqlite3")
            result = worker.run_once()
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(len(queue.fail_calls), 1)
            self.assertEqual(queue.fail_calls[0]["error_code"], "authentication_failed")


    def test_malformed_approval_is_rejected_before_identity_authentication(self):
        cases = (
            ("false", None), (0, None), (None, None),
            (True, "pending"), (True, "rejected"), (True, None),
            (True, "APPROVED"), (False, "approved"), (False, "pending"),
            (False, 0),
        )
        with tempfile.TemporaryDirectory() as directory:
            for approval_required, approval_status in cases:
                with self.subTest(
                    approval_required=approval_required,
                    approval_status=approval_status,
                ):
                    job = {
                        "id": "job-approval", "task_id": "task-approval",
                        "handler": "report.preview", "payload": {},
                        "lease_token": "lease-approval", "attempts": 1, "max_attempts": 5, "agent_identity": None,
                    }
                    queue = QueueSpy(job)
                    queue.store = type("Store", (), {
                        "get_task": lambda self, task_id: {"task": {
                            "id": task_id, "owner_agent": "agent-a",
                            "status": "in_progress",
                            "approval_required": approval_required,
                            "approval_status": approval_status,
                        }}
                    })()
                    registry = HandlerRegistry()
                    registry.register(
                        "report.preview", "read_only",
                        lambda payload, context: self.fail(
                            "Le handler ne doit pas être exécuté."
                        ),
                    )
                    policy = {
                        "execution_enabled": True,
                        "allowed_handlers": ["report.preview"],
                        "action_permissions": {
                            "read_only": {"enabled": True, "owner_approval": False}
                        },
                        "external_actions_enabled": False,
                    }
                    worker = PapiWorker(
                        queue=queue, registry=registry, policy=policy,
                        worker_id="worker-test",
                        audit_path=Path(directory) / "audit.jsonl",
                    )
                    with patch(
                        "papi_core.worker.authorize_authenticated_agent",
                        side_effect=AssertionError("Authentification appelée trop tôt."),
                    ) as authenticate:
                        result = worker.run_once()
                    self.assertEqual(result["status"], "blocked")
                    self.assertEqual(queue.fail_calls[0]["error_code"], "permission_denied")
                    authenticate.assert_not_called()



    def test_general_policy_authorization_runs_after_agent_authentication(self):
        job = {
            "id": "job-policy-order", "task_id": "task-1",
            "handler": "report.preview", "payload": {},
            "lease_token": "lease-policy-order", "attempts": 1, "max_attempts": 5, "agent_identity": {"signed": True},
        }
        queue = QueueSpy(job)
        queue.store = FakeStore()
        registry = HandlerRegistry()
        registry.register("report.preview", "read_only", lambda payload, context: {"ok": True})
        policy = {
            "execution_enabled": True,
            "allowed_handlers": ["report.preview"],
            "action_permissions": {"read_only": {"enabled": True, "owner_approval": False}},
            "external_actions_enabled": False,
        }
        worker = PapiWorker(queue=queue, registry=registry, policy=policy, worker_id="worker-test")
        call_order = []

        def authenticate(*args, **kwargs):
            call_order.append("authenticate")
            return {"principal": type("Principal", (), {"agent_id": "agent-a"})()}

        def deny_policy(*args, **kwargs):
            call_order.append("authorize_policy")
            from papi_core.handler_registry import PermissionError
            raise PermissionError("policy_denied")

        with patch("papi_core.worker.authorize_authenticated_agent", side_effect=authenticate):
            with patch("papi_core.worker.authorize_job", side_effect=deny_policy):
                result = worker.run_once()

        self.assertEqual(call_order, ["authenticate", "authorize_policy"])
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(queue.fail_calls[0]["error_code"], "permission_denied")



    def test_transient_storage_error_is_scheduled_with_durable_attempt_metadata(self):
        from papi_core.storage import StoreError
        job = {"id": "job-transient", "task_id": "task-transient",
               "handler": "report.preview", "payload": {},
               "lease_token": "lease-transient", "attempts": 3,
               "max_attempts": 7, "agent_identity": None}
        queue = QueueSpy(job)
        queue.store = type("Store", (), {
            "get_task": lambda self, task_id: (_ for _ in ()).throw(
                StoreError("temporary outage", retry_code="service_timeout")
            )
        })()
        worker = PapiWorker(queue=queue, registry=HandlerRegistry(),
            policy={"execution_enabled": True}, worker_id="worker-test")
        result = worker.run_once()
        self.assertEqual(result["status"], "retry_scheduled")
        self.assertEqual(queue.fail_calls[0]["error_code"], "service_timeout")
        self.assertEqual(queue.fail_calls[0]["attempt"], 3)
        self.assertEqual(queue.fail_calls[0]["max_attempts"], 7)

    def test_unclassified_storage_error_is_permanent(self):
        from papi_core.storage import StoreError
        job = {"id": "job-storage", "task_id": "task-storage",
               "handler": "report.preview", "payload": {},
               "lease_token": "lease-storage", "attempts": 2,
               "max_attempts": 6, "agent_identity": None}
        queue = QueueSpy(job)
        queue.store = type("Store", (), {
            "get_task": lambda self, task_id: (_ for _ in ()).throw(
                StoreError("validation or permission issue")
            )
        })()
        worker = PapiWorker(queue=queue, registry=HandlerRegistry(),
            policy={"execution_enabled": True}, worker_id="worker-test")
        result = worker.run_once()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(queue.fail_calls[0]["error_code"], "worker_validation_error")
        self.assertEqual(queue.fail_calls[0]["max_attempts"], 6)

    def test_worker_requires_service_identity_when_policy_enables_audience_binding(self):
        with self.assertRaises(WorkerError):
            PapiWorker(queue=QueueSpy(), registry=HandlerRegistry(),
                policy={"execution_enabled": True, "require_service_audience": True},
                worker_id="worker-test")

    def test_worker_uses_service_bound_authorizer_when_configured(self):
        job = {"id": "job-service", "task_id": "task-1", "handler": "report.preview",
               "payload": {}, "lease_token": "lease-service", "attempts": 1, "max_attempts": 5,
               "agent_identity": {"signed": "service-bound"}}
        queue = QueueSpy(job)
        queue.store = FakeStore()
        registry = HandlerRegistry()
        registry.register("report.preview", "read_only", lambda payload, context: {"ok": True})
        policy = {"execution_enabled": True, "require_service_audience": True,
                  "allowed_handlers": ["report.preview"],
                  "action_permissions": {"read_only": {"enabled": True, "owner_approval": False}},
                  "external_actions_enabled": False}
        worker = PapiWorker(queue=queue, registry=registry, policy=policy,
            worker_id="worker-reporting", service_id="reporting-api",
            service_audience="papi-reporting")
        from papi_core.authz import AccessDenied
        with patch("papi_core.worker.authorize_service_agent",
                   side_effect=AccessDenied("wrong audience")) as authorize_service:
            result = worker.run_once()
        self.assertEqual(result["status"], "blocked")
        authorize_service.assert_called_once()
        self.assertEqual(authorize_service.call_args.kwargs["service_id"], "reporting-api")
        self.assertEqual(authorize_service.call_args.kwargs["audience"], "papi-reporting")
        self.assertEqual(queue.fail_calls[0]["error_code"], "authentication_failed")

    def test_worker_rejects_partial_service_configuration(self):
        with self.assertRaises(WorkerError):
            PapiWorker(queue=QueueSpy(), registry=HandlerRegistry(),
                policy={"execution_enabled": True, "require_service_audience": True},
                worker_id="worker-test", service_id="reporting-api")



if __name__ == "__main__":
    unittest.main()
