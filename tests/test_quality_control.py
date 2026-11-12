import pytest

from runtime.papi_core.quality_control import (
    QualityControlError, build_quality_control, build_quality_review_candidate,
)


def review(event_id="review-001", task_id="task-1", result="pass", at="2026-11-12T10:00:00Z"):
    return {
        "event_id": event_id, "occurred_at": at, "actor": "reviewer-1",
        "action": "quality.reviewed", "entity_type": "task", "entity_id": task_id,
        "details": {"result": result, "reviewer_id": "reviewer-1",
                    "criteria_total": 3, "criteria_passed": 3,
                    "evidence_ref": "artifact-v1"},
    }


def test_tasks_without_review_are_not_assumed_to_pass():
    result = build_quality_control([{"id": "task-1", "status": "review"}], [])
    assert result["by_task"][0]["quality_status"] == "awaiting_review"
    assert result["summary"]["review_passed"] == 0


def test_explicit_pass_is_projected_with_evidence():
    result = build_quality_control([{"id": "task-1", "status": "review"}], [review()])
    item = result["by_task"][0]
    assert item["quality_status"] == "review_passed"
    assert item["review"]["event_id"] == "review-001"
    assert item["review"]["criteria_passed"] == 3


def test_failed_review_and_rework_are_distinguished():
    tasks = [{"id": "task-1"}, {"id": "task-2"}]
    events = [review(task_id="task-1", result="fail"),
              review(event_id="review-002", task_id="task-2", result="rework_required")]
    result = build_quality_control(tasks, events)
    assert result["summary"]["review_failed"] == 1
    assert result["summary"]["rework_required"] == 1


def test_latest_review_wins_by_timestamp():
    events = [review(result="pass", at="2026-11-10T10:00:00Z"),
              review(event_id="review-002", result="rework_required", at="2026-11-11T10:00:00Z")]
    result = build_quality_control([{"id": "task-1"}], events)
    assert result["by_task"][0]["quality_status"] == "rework_required"


def test_invalid_review_is_rejected():
    bad = review()
    bad["details"]["criteria_passed"] = 4
    result = build_quality_control([{"id": "task-1"}], [bad])
    assert result["reviews_rejected"] == 1
    assert result["by_task"][0]["quality_status"] == "not_reviewed"


def test_duplicate_task_ids_are_rejected():
    with pytest.raises(QualityControlError):
        build_quality_control([{"id": "task-1"}, {"id": "task-1"}], [])


def test_candidate_requires_all_criteria_for_pass_and_is_not_persisted():
    candidate = build_quality_review_candidate(
        task_id="task-1", reviewer_id="reviewer-1", review_id="rev-001",
        criteria=[{"criterion_id": "accuracy", "passed": True},
                  {"criterion_id": "completeness", "passed": False}],
        evidence_ref="artifact-v2", occurred_at="2026-11-12T10:00:00Z",
    )
    assert candidate["result"] == "rework_required"
    assert candidate["persisted"] is False
    assert candidate["task_changed"] is False


def test_candidate_rejects_duplicate_criteria():
    with pytest.raises(QualityControlError):
        build_quality_review_candidate(
            task_id="task-1", reviewer_id="reviewer-1", review_id="rev-002",
            criteria=[{"criterion_id": "same", "passed": True},
                      {"criterion_id": "same", "passed": True}],
            evidence_ref="artifact-v2", occurred_at="2026-11-12T10:00:00Z",
        )


def test_read_only_controls_are_explicit():
    result = build_quality_control([], [])
    assert result["controls"]["actions_executed"] == 0
    assert result["controls"]["tasks_changed"] == 0
    assert result["controls"]["deliverable_content_inspected"] is False
