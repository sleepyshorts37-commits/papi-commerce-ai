import copy
import unittest

from papi_core.worker_runtime import WorkerRuntimeError, run_worker_job


def fixtures():
    agent = {"id": "agent-a", "name": "Agent A", "status": "active",
             "permissions": ["read_reports"], "prohibited": ["spend_money"]}
    identity = {
        "identity_id": "PAPI-AGENT-A", "agent_id": "agent-a",
        "full_name": "Agent A", "role": "Analyste", "department": "Analyse",
        "manager_id": "manager", "mission": "Lire les rapports autorisés.",
        "competencies": ["analyse"], "objectives": ["préparer un rapport"],
        "autonomy_level": "bounded", "permissions": ["read_reports"],
        "prohibited_actions": ["spend_money"], "status": "active",
        "created_at": "2026-11-12T00:00:00Z", "assignment_history": [],
        "evaluation_history": [], "profile_state": "complete",
    }
    task = {
        "id": "TASK-1", "owner_agent": "agent-a", "status": "ready",
        "approval_required": False,
        "execution": {"handler": "internal.echo", "permission": "read_reports",
                      "category": "read_only", "cost_xof": 0},
    }
    policy = {
        "execution_enabled": True, "default_budget_xof": 0,
        "external_actions_enabled": False, "allowed_handlers": ["internal.echo"],
        "action_permissions": {
            "read_only": {"enabled": True}, "internal_write": {"enabled": True},
            "external_communication": {"enabled": False}, "financial": {"enabled": False},
            "legal": {"enabled": False}},
        "requires_owner_approval": [], "never_allowed": [],
    }
    job = {"id": "JOB-1", "task_id": "TASK-1", "handler": "internal.echo",
           "status": "running", "payload": {"hello": "papi"}}
    auth = {"worker_authenticated": True, "worker_id": "agent-a",
            "operation": "heartbeat", "job_id": "JOB-1"}
    return job, task, agent, identity, policy, auth


class WorkerRuntimeTests(unittest.TestCase):
    def test_default_policy_holds_without_invoking_handler(self):
        job, task, agent, identity, policy, auth = fixtures()
        policy["execution_enabled"] = False
        calls = []
        result = run_worker_job(job=job, task=task, agent=agent, identity=identity,
            policy=policy, auth_envelope={}, authenticate=lambda _: auth,
            handlers={"internal.echo": lambda p: calls.append(p) or p})
        self.assertEqual(result["status"], "held")
        self.assertFalse(result["handler_invoked"])
        self.assertEqual(calls, [])

    def test_authenticated_internal_handler_executes_when_explicitly_enabled(self):
        job, task, agent, identity, policy, auth = fixtures()
        result = run_worker_job(job=job, task=task, agent=agent, identity=identity,
            policy=policy, auth_envelope={"signed": True},
            authenticate=lambda _: auth)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["result"], {"echo": {"hello": "papi"}})

    def test_authentication_failure_fails_closed(self):
        job, task, agent, identity, policy, _ = fixtures()
        with self.assertRaises(WorkerRuntimeError):
            run_worker_job(job=job, task=task, agent=agent, identity=identity,
                policy=policy, auth_envelope={}, authenticate=lambda _: {})
    
    def test_wrong_job_proof_is_rejected(self):
        job, task, agent, identity, policy, auth = fixtures()
        auth["job_id"] = "JOB-OTHER"
        with self.assertRaises(WorkerRuntimeError):
            run_worker_job(job=job, task=task, agent=agent, identity=identity,
                policy=policy, auth_envelope={}, authenticate=lambda _: auth)

    def test_job_handler_must_match_task_specification(self):
        job, task, agent, identity, policy, auth = fixtures()
        job["handler"] = "shell.run"
        with self.assertRaises(WorkerRuntimeError):
            run_worker_job(job=job, task=task, agent=agent, identity=identity,
                policy=policy, auth_envelope={}, authenticate=lambda _: auth)

    def test_unregistered_handler_is_blocked(self):
        job, task, agent, identity, policy, auth = fixtures()
        task["execution"]["handler"] = "shell.run"
        job["handler"] = "shell.run"
        policy["allowed_handlers"].append("shell.run")
        result = run_worker_job(job=job, task=task, agent=agent, identity=identity,
            policy=policy, auth_envelope={}, authenticate=lambda _: auth,
            handlers={})
        self.assertEqual(result["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
