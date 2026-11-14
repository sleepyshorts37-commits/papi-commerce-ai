import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from papi_core.identity_ed25519 import provision_ed25519_agent, sign_ed25519_request
from papi_core.principal import _issue_authenticated_agent_principal
from papi_core.reconciliation import build_reconciliation_preview
from papi_core.sync_protocol import build_sync_plan
from papi_core.sync_approval import SyncApprovalError, verify_sync_plan_approval


NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)


class SyncApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.keys = root / "keys"
        self.registry = root / "public.json"
        self.replay = root / "replay.sqlite3"
        self.private = provision_ed25519_agent("owner-001", self.keys, self.registry)
        self.principal = _issue_authenticated_agent_principal("agent-1")
        memory = {"memory_id": "M-1", "event_type": "remember", "scope": "shared",
                  "sensitivity": "normal", "category": "fact", "title": "T",
                  "content": "C", "source_type": "test", "source_id": "1",
                  "confidence": 1.0, "tags": []}
        preview = build_reconciliation_preview(
            principal=self.principal, local_memory=[memory], remote_memory=[],
            local_messages=[], remote_messages=[])
        self.plan = build_sync_plan(principal=self.principal, preview=preview,
                                    destination_instance="instance-b", plan_id="plan-33")
        self.task = {"task_id": "task-33", "status": "in_progress"}
        self.policy = {"owner_id": "owner-001", "max_approval_ttl_seconds": 900}

    def tearDown(self):
        self.temp.cleanup()

    def envelope(self, **changes):
        payload = {
            "approval_id": "APR-33-0001", "task_id": "task-33",
            "handler": "sync.apply_plan", "action_class": "internal_write",
            "decision": "approved", "approved_by": "owner-001",
            "approved_at": "2026-11-14T12:00:00Z",
            "expires_at": "2026-11-14T12:10:00Z",
            "plan_digest": self.plan["plan_digest"],
            "destination_instance": self.plan["destination_instance"],
            "action_ids": [a["action_id"] for a in self.plan["actions"]],
        }
        payload.update(changes)
        return sign_ed25519_request("owner-001", payload, self.private,
                                    timestamp=int(NOW.timestamp()), nonce="nonce-approval-33-0001")

    def verify(self, envelope=None):
        return verify_sync_plan_approval(
            envelope=envelope or self.envelope(), plan=self.plan, task=self.task,
            policy=self.policy, registry_path=self.registry, replay_db=self.replay,
            now_epoch=int(NOW.timestamp()), now=NOW)

    def test_valid_owner_signature_is_bound_to_exact_plan(self):
        result = self.verify()
        self.assertEqual(result["plan_digest"], self.plan["plan_digest"])
        self.assertEqual(result["destination_instance"], "instance-b")
        self.assertTrue(result["signature_verified"])
        self.assertFalse(result["execution_enabled"])
        self.assertTrue(result["durable_consumption_required"])

    def test_rejects_wrong_digest_destination_or_action_set(self):
        for change in (
            {"plan_digest": "0" * 64},
            {"destination_instance": "instance-c"},
            {"action_ids": []},
        ):
            with self.subTest(change=change), self.assertRaises(SyncApprovalError):
                self.verify(self.envelope(**change))

    def test_rejects_non_owner_signature(self):
        root = Path(self.temp.name)
        other_keys, other_registry = root / "other", root / "other.json"
        other_private = provision_ed25519_agent("agent-1", other_keys, other_registry)
        payload = self.envelope()["payload"]
        forged = sign_ed25519_request("agent-1", payload, other_private,
                                      timestamp=int(NOW.timestamp()), nonce="nonce-approval-33-0002")
        with self.assertRaises(SyncApprovalError):
            verify_sync_plan_approval(
                envelope=forged, plan=self.plan, task=self.task, policy=self.policy,
                registry_path=other_registry, replay_db=root / "other.sqlite3",
                now_epoch=int(NOW.timestamp()), now=NOW)

    def test_rejects_invalid_task_and_expired_approval(self):
        with self.assertRaises(SyncApprovalError):
            verify_sync_plan_approval(
                envelope=self.envelope(), plan=self.plan,
                task={"task_id": "other", "status": "in_progress"},
                policy=self.policy, registry_path=self.registry, replay_db=self.replay,
                now_epoch=int(NOW.timestamp()), now=NOW)
        with self.assertRaises(SyncApprovalError):
            self.verify(self.envelope(expires_at="2026-11-14T11:59:00Z"))

    def test_replay_is_rejected(self):
        envelope = self.envelope()
        self.verify(envelope)
        with self.assertRaises(SyncApprovalError):
            self.verify(envelope)


if __name__ == "__main__":
    unittest.main()
