from copy import deepcopy

import pytest

from runtime.papi_core.incident_response_planner import (
    IncidentResponsePlannerError,
    build_incident_response_plan,
)


def incident(incident_id, severity="warning", category="worker", status="open"):
    return {"incident_id": incident_id, "severity": severity,
            "category": category, "status": status}


def test_critical_security_incident_gets_top_priority_and_owner_escalation():
    result = build_incident_response_plan({"incidents": [
        incident("sec-1", "critical", "security")
    ]})
    plan = result["plans"][0]
    assert plan["priority"] == 1
    assert plan["owner_escalation_required"] is True
    assert plan["approval_required_from"] == "owner_or_authorized_manager"
    assert plan["execution_authorized"] is False


def test_plans_are_sorted_and_resolved_incidents_are_excluded():
    result = build_incident_response_plan({"incidents": [
        incident("z", "info", "other"),
        incident("closed", "critical", "job", "resolved"),
        incident("b", "critical", "job"),
        incident("a", "critical", "worker"),
    ]})
    assert [item["incident_id"] for item in result["plans"]] == ["a", "b", "z"]
    assert result["summary"]["resolved_incidents_excluded"] == 1


def test_all_categories_have_controlled_review_steps():
    categories = ["worker", "security", "job", "platform", "data", "integration", "other"]
    result = build_incident_response_plan({"incidents": [
        incident(f"i-{category}", "warning", category) for category in categories
    ]})
    assert len(result["plans"]) == len(categories)
    assert all(plan["steps"] for plan in result["plans"])


def test_preview_does_not_mutate_input_or_execute_actions():
    source = {"incidents": [incident("i-1", "critical", "job")]}
    original = deepcopy(source)
    result = build_incident_response_plan(source)
    assert source == original
    assert result["read_only"] is True
    assert result["writes_performed"] == 0
    assert result["actions_executed"] == 0
    assert result["notifications_sent"] == 0
    assert all(not plan["execution_authorized"] for plan in result["plans"])


@pytest.mark.parametrize("source", [
    None,
    {},
    {"incidents": "not-a-list"},
    {"incidents": [None]},
    {"incidents": [incident("", "warning", "worker")]},
    {"incidents": [incident("i", "urgent", "worker")]},
    {"incidents": [incident("i", "warning", "unknown")]},
    {"incidents": [incident("i", "warning", "worker", "pending")]},
    {"incidents": [incident("same"), incident("same")]},
])
def test_invalid_snapshot_fails_closed(source):
    with pytest.raises(IncidentResponsePlannerError):
        build_incident_response_plan(source)
