import json
import tempfile
import unittest
from pathlib import Path
from papi_core.security import SecurityError, check_security, security_report, validate_policy

def policy():
    return {"project":"PAPI COMMERCE AI","execution_enabled":False,"external_actions_enabled":False,
      "default_budget_xof":0,"agent_execution_status":"not_deployed",
      "action_permissions":{"external_communication":{"enabled":False,"owner_approval":True},
        "financial":{"enabled":False,"owner_approval":True},"legal":{"enabled":False,"owner_approval":True}},
      "never_allowed":["store_credentials_in_repository","request_otp_or_pin_in_chat","impersonate_people",
        "spam_or_evade_platform_limits","fabricate_revenue_or_sales","bypass_kyc_or_access_controls"]}

class SecurityTests(unittest.TestCase):
    def test_safe_policy_passes(self):
        self.assertEqual(validate_policy(policy()),[])
    def test_execution_must_remain_disabled(self):
        data=policy(); data["execution_enabled"]=True
        self.assertTrue(any("execution_enabled" in e for e in validate_policy(data)))
    def test_external_communications_must_remain_disabled(self):
        data=policy(); data["action_permissions"]["external_communication"]["enabled"]=True
        self.assertTrue(validate_policy(data))
    def test_budget_must_remain_zero(self):
        data=policy(); data["default_budget_xof"]=100
        self.assertTrue(validate_policy(data))
    def test_missing_prohibitions_are_rejected(self):
        data=policy(); data["never_allowed"]=[]
        self.assertTrue(validate_policy(data))
    def test_report_checks_gitignore(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/".gitignore").write_text(".env\n.env.*\n!.env.example\n",encoding="utf-8")
            p=root/"policy.json"; p.write_text(json.dumps(policy()),encoding="utf-8")
            self.assertEqual(check_security(p,root)["status"],"safe_scaffold")
    def test_missing_env_ignore_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/".gitignore").write_text("*.pyc\n",encoding="utf-8")
            p=root/"policy.json"; p.write_text(json.dumps(policy()),encoding="utf-8")
            with self.assertRaises(SecurityError): check_security(p,root)

if __name__=="__main__": unittest.main()
