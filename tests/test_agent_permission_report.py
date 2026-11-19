import json
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from papi_core.agent_permission_report import build_agent_permission_report
from papi_core.__main__ import main


def safe_policy():
    return {
        "project": "PAPI COMMERCE AI",
        "execution_enabled": False,
        "external_actions_enabled": False,
        "default_budget_xof": 0,
        "agent_execution_status": "not_deployed",
        "action_permissions": {
            "external_communication": {"enabled": False, "owner_approval": True},
            "financial": {"enabled": False, "owner_approval": True},
            "legal": {"enabled": False, "owner_approval": True},
        },
        "never_allowed": [
            "store_credentials_in_repository",
            "request_otp_or_pin_in_chat",
            "impersonate_people",
            "spam_or_evade_platform_limits",
            "fabricate_revenue_or_sales",
            "bypass_kyc_or_access_controls",
        ],
    }


def write_registry(root, agents):
    path = root / "agents.json"
    path.write_text(json.dumps({"project": "PAPI COMMERCE AI", "agents": agents}), encoding="utf-8")
    return path


def write_policy(root, policy=None):
    path = root / "policy.json"
    path.write_text(json.dumps(policy or safe_policy()), encoding="utf-8")
    return path


def agent(status="active", permissions=None, prohibited=None):
    return {
        "id": "agent-a",
        "name": "Agent A",
        "status": status,
        "permissions": permissions if permissions is not None else ["read_reports"],
        "prohibited": prohibited if prohibited is not None else [],
    }


class AgentPermissionReportTests(unittest.TestCase):
    def test_active_declared_permission_is_only_a_local_allow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agents_path = write_registry(root, [agent()])
            policy_path = write_policy(root)
            report = build_agent_permission_report(agents_path, policy_path)
        item = report["agents"][0]["permissions"][0]
        self.assertEqual(report["status"], "ok")
        self.assertEqual(item["local_check"], "allow")
        self.assertEqual(item["runtime_gate"], "blocked")
        self.assertIn("execution_disabled", item["runtime_blockers"])
        self.assertFalse(report["runtime_execution_available"])
        self.assertFalse(report["identity_authenticated"])

    def test_planned_agent_is_denied_even_when_permission_is_declared(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agents_path = write_registry(root, [agent(status="planned")])
            policy_path = write_policy(root)
            report = build_agent_permission_report(agents_path, policy_path)
        item = report["agents"][0]["permissions"][0]
        self.assertEqual(item["local_check"], "deny")
        self.assertIn("agent_not_active", item["runtime_blockers"])

    def test_explicit_prohibition_overrides_permission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agents_path = write_registry(root, [agent(prohibited=["read_reports"])])
            policy_path = write_policy(root)
            report = build_agent_permission_report(agents_path, policy_path)
        item = report["agents"][0]["permissions"][0]
        self.assertEqual(item["local_check"], "deny")
        self.assertTrue(item["explicitly_prohibited"])
        self.assertIn("explicit_agent_prohibition", item["runtime_blockers"])

    def test_malformed_permission_list_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agents_path = write_registry(root, [{**agent(), "permissions": "read_reports"}])
            policy_path = write_policy(root)
            report = build_agent_permission_report(agents_path, policy_path)
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(report["errors"])
        self.assertEqual(report["summary"]["local_allow"], 0)

    def test_invalid_permission_token_is_reported_and_not_authorized(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agents_path = write_registry(root, [agent(permissions=["read_reports", "Bad Permission"])])
            policy_path = write_policy(root)
            report = build_agent_permission_report(agents_path, policy_path)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["agents"][0]["permissions"][0]["local_check"], "deny")
        self.assertTrue(report["agents"][0]["errors"])

    def test_duplicate_and_overlapping_permissions_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agents_path = write_registry(root, [agent(permissions=["read_reports", "read_reports"], prohibited=["read_reports"])])
            policy_path = write_policy(root)
            report = build_agent_permission_report(agents_path, policy_path)
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(any("doublons" in error for error in report["agents"][0]["errors"]))
        self.assertTrue(any("également interdites" in error for error in report["agents"][0]["errors"]))

    def test_invalid_global_policy_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agents_path = write_registry(root, [agent()])
            policy = safe_policy()
            policy["execution_enabled"] = True
            policy_path = write_policy(root, policy)
            report = build_agent_permission_report(agents_path, policy_path)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["agents"][0]["permissions"][0]["local_check"], "deny")
        self.assertTrue(report["policy_validation_errors"])

    def test_missing_registry_or_policy_returns_blocked_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = build_agent_permission_report(root / "missing-agents.json", root / "missing-policy.json")
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["runtime_execution_available"])
        self.assertEqual(report["agents"], [])

    def test_committed_roster_report_never_claims_runtime_access(self):
        report = build_agent_permission_report()
        self.assertFalse(report["runtime_execution_available"])
        self.assertFalse(report["identity_authenticated"])
        self.assertFalse(report["handler_execution_verified"])
        for item in report["agents"]:
            for permission in item["permissions"]:
                self.assertEqual(permission["runtime_gate"], "blocked")

    def test_cli_emits_json_report_without_external_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agents_path = write_registry(root, [agent()])
            policy_path = write_policy(root)
            output = StringIO()
            with patch("sys.argv", ["papi", "agent-permission-report", "--agents", str(agents_path), "--policy", str(policy_path)]):
                with redirect_stdout(output):
                    exit_code = main()
        self.assertEqual(exit_code, 0)
        parsed = json.loads(output.getvalue())
        self.assertEqual(parsed["mode"], "read_only_local")
        self.assertFalse(parsed["runtime_execution_available"])


if __name__ == "__main__":
    unittest.main()
