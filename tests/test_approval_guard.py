"""Tests déterministes des approbations humaines à portée limitée."""
import unittest
from datetime import datetime, timezone

from papi_core.approval_guard import ApprovalDenied, authorize_scoped_approval


NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)
TASK = {"task_id": "TASK-25-001", "status": "in_progress"}
POLICY = {"owner_id": "owner-001", "max_approval_ttl_seconds": 900}


def approval(**changes):
    record = {
        "approval_id": "APR-0001",
        "task_id": "TASK-25-001",
        "handler": "external.email.send",
        "action_class": "external_communication",
        "decision": "approved",
        "approved_by": "owner-001",
        "approved_at": "2026-11-14T12:00:00Z",
        "expires_at": "2026-11-14T12:10:00Z",
    }
    record.update(changes)
    return record


class ScopedApprovalTests(unittest.TestCase):
    def validate(self, record=None, **kwargs):
        return authorize_scoped_approval(
            approval=record or approval(),
            task=TASK,
            handler="external.email.send",
            action_class="external_communication",
            policy=POLICY,
            now=NOW,
            **kwargs,
        )

    def test_accepts_owner_approval_bound_to_exact_action(self):
        result = self.validate()
        self.assertEqual(result["approval_id"], "APR-0001")
        self.assertEqual(result["handler"], "external.email.send")

    def test_rejects_non_owner(self):
        with self.assertRaises(ApprovalDenied):
            self.validate(approval(approved_by="agent-ibrahima"))

    def test_rejects_other_task_or_action(self):
        with self.assertRaises(ApprovalDenied):
            self.validate(approval(task_id="TASK-OTHER"))
        with self.assertRaises(ApprovalDenied):
            self.validate(approval(handler="external.social.publish"))

    def test_rejects_replay(self):
        with self.assertRaises(ApprovalDenied):
            self.validate(consumed_approval_ids={"APR-0001"})

    def test_rejects_expired_or_overlong_approval(self):
        with self.assertRaises(ApprovalDenied):
            self.validate(approval(expires_at="2026-11-14T11:59:59Z"))
        with self.assertRaises(ApprovalDenied):
            self.validate(approval(expires_at="2026-11-14T13:00:00Z"))

    def test_rejects_naive_timestamps_and_pending_decision(self):
        with self.assertRaises(ApprovalDenied):
            self.validate(approval(approved_at="2026-11-14T12:00:00"))
        with self.assertRaises(ApprovalDenied):
            self.validate(approval(decision="pending"))

    def test_rejects_task_not_in_progress(self):
        with self.assertRaises(ApprovalDenied):
            authorize_scoped_approval(
                approval=approval(), task={"task_id": "TASK-25-001", "status": "queued"},
                handler="external.email.send", action_class="external_communication",
                policy=POLICY, now=NOW,
            )


if __name__ == "__main__":
    unittest.main()
