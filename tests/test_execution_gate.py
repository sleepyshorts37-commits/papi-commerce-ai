from datetime import datetime, timezone

from papi_core.execution_gate import evaluate_execution_readiness


def fixtures():
    agent = {
        "id": "agent-a", "name": "Agent A", "status": "active",
        "permissions": ["read_reports"], "prohibited": ["spend_money"],
    }
    identity = {
        "identity_id": "PAPI-AGENT-A", "agent_id": "agent-a",
        "full_name": "Agent A", "role": "Analyste", "department": "Analyse",
        "manager_id": "manager", "mission": "Lire les rapports autorisés.",
        "competencies": ["analyse"], "objectives": ["préparer un rapport"],
        "autonomy_level": "bounded", "permissions": ["read_reports"],
        "prohibited_actions": ["spend_money"], "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "assignment_history": [], "evaluation_history": [], "profile_state": "complete",
    }
    task = {
        "id": "TASK-1", "owner_agent": "agent-a", "status": "ready",
        "approval_required": False,
        "execution": {
            "handler": "internal.echo", "permission": "read_reports",
            "category": "read_only", "cost_xof": 0,
        },
    }
    policy = {
        "execution_enabled": True, "default_budget_xof": 0,
        "external_actions_enabled": False,
        "allowed_handlers": ["internal.echo"],
        "action_permissions": {
            "read_only": {"enabled": True},
            "internal_write": {"enabled": True},
            "external_communication": {"enabled": False},
            "financial": {"enabled": False}, "legal": {"enabled": False},
        },
        "requires_owner_approval": ["send_outbound_messages"],
        "never_allowed": ["impersonate_people"],
    }
    return task, agent, identity, policy


def test_default_disabled_policy_blocks_execution():
    task, agent, identity, policy = fixtures()
    policy["execution_enabled"] = False
    result = evaluate_execution_readiness(task, agent, identity, policy)
    assert result["eligible"] is False
    assert "EXECUTION_DISABLED" in {item["code"] for item in result["reason_codes"]}
    assert result["execution_performed"] is False
    assert result["execution_token_issued"] is False


def test_valid_internal_zero_cost_task_passes_preflight_only():
    task, agent, identity, policy = fixtures()
    result = evaluate_execution_readiness(task, agent, identity, policy)
    assert result["eligible"] is True
    assert result["decision"] == "preflight_passed"
    assert result["execution_performed"] is False
    assert result["mode"] == "preflight_only"


def test_inactive_agent_is_blocked():
    task, agent, identity, policy = fixtures()
    agent["status"] = "planned"
    result = evaluate_execution_readiness(task, agent, identity, policy)
    assert "AGENT_INACTIVE" in {item["code"] for item in result["reason_codes"]}


def test_incomplete_identity_is_blocked():
    task, agent, identity, policy = fixtures()
    identity["profile_state"] = "incomplete"
    result = evaluate_execution_readiness(task, agent, identity, policy)
    assert "IDENTITY_INCOMPLETE" in {item["code"] for item in result["reason_codes"]}


def test_missing_permission_is_blocked():
    task, agent, identity, policy = fixtures()
    task["execution"]["permission"] = "send_message"
    result = evaluate_execution_readiness(task, agent, identity, policy)
    assert "PERMISSION_NOT_GRANTED" in {item["code"] for item in result["reason_codes"]}


def test_pending_approval_is_blocked():
    task, agent, identity, policy = fixtures()
    task["approval_required"] = True
    task["approval_status"] = "pending"
    result = evaluate_execution_readiness(task, agent, identity, policy)
    assert "OWNER_APPROVAL_REQUIRED" in {item["code"] for item in result["reason_codes"]}


def test_not_ready_task_is_blocked():
    task, agent, identity, policy = fixtures()
    task["status"] = "in_progress"
    result = evaluate_execution_readiness(task, agent, identity, policy)
    assert "TASK_NOT_READY" in {item["code"] for item in result["reason_codes"]}


def test_external_communication_is_blocked_by_policy():
    task, agent, identity, policy = fixtures()
    task["execution"]["category"] = "external_communication"
    task["execution"]["permission"] = "read_reports"
    result = evaluate_execution_readiness(task, agent, identity, policy)
    assert "ACTION_CATEGORY_DISABLED" in {item["code"] for item in result["reason_codes"]}
    assert "EXTERNAL_ACTIONS_DISABLED" in {item["code"] for item in result["reason_codes"]}


def test_nonzero_cost_exceeds_zero_budget():
    task, agent, identity, policy = fixtures()
    task["execution"]["cost_xof"] = 1
    result = evaluate_execution_readiness(task, agent, identity, policy)
    assert "BUDGET_EXCEEDED" in {item["code"] for item in result["reason_codes"]}


def test_agent_prohibition_is_enforced():
    task, agent, identity, policy = fixtures()
    task["execution"]["permission"] = "spend_money"
    agent["permissions"].append("spend_money")
    identity["permissions"].append("spend_money")
    result = evaluate_execution_readiness(task, agent, identity, policy)
    assert "ACTION_PROHIBITED" in {item["code"] for item in result["reason_codes"]}
