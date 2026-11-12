from datetime import datetime, timezone

import pytest

from papi_core.task_lease import (
    TaskLeaseError, claim_task, expire_task_lease, heartbeat_task,
)


def _fixtures():
    task = {
        "id": "TASK-LEASE-1", "owner_agent": "worker-a",
        "status": "ready", "approval_required": False,
    }
    agent = {"id": "worker-a", "status": "active"}
    return task, agent


def test_claim_creates_bounded_lease_without_mutating_input():
    task, agent = _fixtures()
    updated, event = claim_task(
        task, agent, lease_id="LEASE-1",
        now="2026-11-12T10:00:00Z", lease_seconds=60,
    )
    assert task["status"] == "ready"
    assert updated["status"] == "in_progress"
    assert updated["worker_lease"]["expires_at"] == "2026-11-12T10:01:00Z"
    assert event["action"] == "task.lease_claimed"


def test_claim_rejects_inactive_or_wrong_owner():
    task, agent = _fixtures()
    agent["status"] = "planned"
    with pytest.raises(TaskLeaseError):
        claim_task(task, agent, lease_id="L1", now="2026-11-12T10:00:00Z")
    agent["status"] = "active"
    agent["id"] = "worker-b"
    with pytest.raises(TaskLeaseError):
        claim_task(task, agent, lease_id="L1", now="2026-11-12T10:00:00Z")


def test_claim_rejects_pending_owner_approval():
    task, agent = _fixtures()
    task.update(approval_required=True, approval_status="pending")
    with pytest.raises(TaskLeaseError):
        claim_task(task, agent, lease_id="L1", now="2026-11-12T10:00:00Z")


def test_heartbeat_renews_only_matching_unexpired_lease():
    task, agent = _fixtures()
    claimed, _ = claim_task(task, agent, lease_id="L1", now="2026-11-12T10:00:00Z", lease_seconds=60)
    renewed, event = heartbeat_task(
        claimed, worker_id="worker-a", lease_id="L1",
        now="2026-11-12T10:00:30Z", lease_seconds=90,
    )
    assert renewed["worker_lease"]["expires_at"] == "2026-11-12T10:02:00Z"
    assert event["action"] == "task.lease_heartbeat"
    with pytest.raises(TaskLeaseError):
        heartbeat_task(renewed, worker_id="worker-b", lease_id="L1", now="2026-11-12T10:00:40Z")


def test_expired_lease_cannot_be_renewed():
    task, agent = _fixtures()
    claimed, _ = claim_task(task, agent, lease_id="L1", now="2026-11-12T10:00:00Z", lease_seconds=30)
    with pytest.raises(TaskLeaseError):
        heartbeat_task(claimed, worker_id="worker-a", lease_id="L1", now="2026-11-12T10:00:30Z")


def test_expiry_returns_task_to_ready_and_clears_lease():
    task, agent = _fixtures()
    claimed, _ = claim_task(task, agent, lease_id="L1", now="2026-11-12T10:00:00Z", lease_seconds=30)
    assert expire_task_lease(claimed, now="2026-11-12T10:00:29Z") is None
    result = expire_task_lease(claimed, now="2026-11-12T10:00:30Z")
    updated, event = result
    assert updated["status"] == "ready"
    assert "worker_lease" not in updated
    assert event["action"] == "task.lease_expired"


def test_lease_duration_is_bounded():
    task, agent = _fixtures()
    with pytest.raises(TaskLeaseError):
        claim_task(task, agent, lease_id="L1", now="2026-11-12T10:00:00Z", lease_seconds=5)
