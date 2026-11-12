import pytest

from runtime.papi_core.approval_center import (
    ApprovalCenterError,
    build_approval_center,
    build_approval_decision_candidate,
)

TIME = "2026-11-12T10:00:00Z"


def event(event_id, actor, action, entity_id, details):
    return {"event_id": event_id, "occurred_at": TIME, "actor": actor,
            "action": action, "entity_type": "approval",
            "entity_id": entity_id, "details": details}


def requested():
    return event("evt-request-1", "astou", "approval.requested", "req-1", {
        "action_type": "publish_public_content",
        "description": "Publier le catalogue commercial validé",
        "risk": "high", "requested_by": "agent-marketing",
        "required_approver": "owner",
    })


def test_projection_tracks_pending_approved_and_rejected():
    first = requested()
    approved = event("evt-decision-1", "owner", "approval.approved", "req-1", {})
    result = build_approval_center([first, approved])
    assert result["requests"][0]["status"] == "approved"
    assert result["summary"]["approved"] == 1
    assert result["writes_performed"] == 0


def test_rejection_is_auditable():
    result = build_approval_center([
        requested(), event("evt-decision-2", "owner", "approval.rejected", "req-1", {})
    ])
    request = result["requests"][0]
    assert request["status"] == "rejected"
    assert len(request["history"]) == 2


def test_only_required_approver_can_decide():
    with pytest.raises(ApprovalCenterError):
        build_approval_center([
            requested(), event("evt-decision-3", "agent-marketing",
                               "approval.approved", "req-1", {})
        ])


def test_decision_candidate_requires_configured_owner_and_pending_request():
    request = {"request_id": "req-1", "status": "pending"}
    result = build_approval_decision_candidate(
        request, decision="approve", actor="owner", owner_actor="owner",
        occurred_at=TIME, decision_id="evt-approval-1"
    )
    assert result["event"]["action"] == "approval.approved"
    assert result["writes_performed"] == 0
    assert result["actions_executed"] == 0


@pytest.mark.parametrize("actor,owner,decision,status", [
    ("agent", "owner", "approve", "pending"),
    ("owner", "owner", "execute", "pending"),
    ("owner", "owner", "approve", "approved"),
])
def test_decision_candidate_fails_closed(actor, owner, decision, status):
    with pytest.raises(ApprovalCenterError):
        build_approval_decision_candidate(
            {"request_id": "req-1", "status": status},
            decision=decision, actor=actor, owner_actor=owner,
            occurred_at=TIME, decision_id="evt-approval-2"
        )


@pytest.mark.parametrize("events", [
    None,
    [event("evt-1", "astou", "approval.requested", "req-1", {})],
    [requested(), event("evt-2", "owner", "approval.approved", "req-1", {}),
     event("evt-3", "owner", "approval.rejected", "req-1", {})],
    [requested(), event("evt-2", "owner", "approval.approved", "missing", {})],
])
def test_invalid_approval_history_fails_closed(events):
    with pytest.raises(ApprovalCenterError):
        build_approval_center(events)
