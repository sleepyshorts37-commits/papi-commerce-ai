import unittest

from papi_core.handler_registry import (
    HandlerRegistry,
    PermissionError,
    authorize_job,
)


class ApprovalStateFailClosedTests(unittest.TestCase):
    def setUp(self):
        self.registry = HandlerRegistry()
        self.registry.register("report.preview", "read_only", lambda payload, context: {"ok": True})
        self.job = {"handler": "report.preview", "payload": {}}
        self.policy = {
            "allowed_handlers": ["report.preview"],
            "execution_enabled": True,
            "action_permissions": {"read_only": {"enabled": True, "owner_approval": False}},
            "external_actions_enabled": False,
        }
        self.task = {
            "status": "in_progress",
            "approval_required": False,
        }

    def test_explicit_no_approval_required_is_accepted(self):
        self.assertEqual(
            authorize_job(self.job, self.task, self.policy, self.registry).name,
            "report.preview",
        )

    def test_truthy_or_falsy_strings_are_not_approval_booleans(self):
        for value in ("true", "false", 1, 0, None):
            with self.subTest(value=value):
                task = {**self.task, "approval_required": value}
                with self.assertRaises(PermissionError):
                    authorize_job(self.job, task, self.policy, self.registry)

    def test_required_approval_needs_approved_status(self):
        for status in (None, "not_required", "pending", "rejected"):
            with self.subTest(status=status):
                task = {"status": "in_progress", "approval_required": True}
                if status is not None:
                    task["approval_status"] = status
                with self.assertRaises(PermissionError):
                    authorize_job(self.job, task, self.policy, self.registry)

    def test_invalid_approval_status_fails_closed(self):
        for status in ("APPROVED", "yes", "", [], {}):
            with self.subTest(status=status):
                task = {**self.task, "approval_status": status}
                with self.assertRaises(PermissionError):
                    authorize_job(self.job, task, self.policy, self.registry)

    def test_approval_state_cannot_conflict_with_not_required(self):
        for status in ("pending", "approved", "rejected"):
            with self.subTest(status=status):
                task = {**self.task, "approval_status": status}
                with self.assertRaises(PermissionError):
                    authorize_job(self.job, task, self.policy, self.registry)

    def test_approved_required_task_is_accepted(self):
        task = {
            "status": "in_progress",
            "approval_required": True,
            "approval_status": "approved",
        }
        self.assertEqual(
            authorize_job(self.job, task, self.policy, self.registry).name,
            "report.preview",
        )


if __name__ == "__main__":
    unittest.main()
