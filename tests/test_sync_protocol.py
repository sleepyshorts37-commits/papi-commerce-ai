import unittest

from papi_core.principal import _issue_authenticated_agent_principal
from papi_core.reconciliation import build_reconciliation_preview
from papi_core.sync_protocol import SyncProtocolError, build_sync_plan, validate_plan_integrity


class ControlledSyncProtocolTests(unittest.TestCase):
    def setUp(self):
        self.principal = _issue_authenticated_agent_principal("astou")
        self.memory = {
            "memory_id": "MEM-1", "event_type": "remember", "scope": "shared",
            "sensitivity": "normal", "category": "fact", "title": "Fait",
            "content": "Valeur de test", "source_type": "test", "source_id": "fixture",
            "confidence": 0.9, "tags": [],
        }
        self.message = {
            "message_id": "MSG-1", "sender": "astou", "recipient": "all",
            "subject": "Test", "body": "Message de test", "message_type": "report",
        }

    def preview(self, **overrides):
        args = dict(local_memory=[self.memory], remote_memory=[],
                    local_messages=[self.message], remote_messages=[])
        args.update(overrides)
        return build_reconciliation_preview(principal=self.principal, **args)

    def test_creates_reference_only_plan_without_writes(self):
        plan = build_sync_plan(principal=self.principal, preview=self.preview(),
                               destination_instance="instance-b", plan_id="plan-001")
        self.assertEqual(len(plan["actions"]), 2)
        self.assertFalse(plan["execution_enabled"])
        self.assertFalse(plan["writes_performed"])
        self.assertTrue(plan["requires_human_approval"])
        self.assertTrue(validate_plan_integrity(plan))
        self.assertNotIn("content", str(plan))
        self.assertNotIn("body", str(plan))

    def test_same_inputs_produce_same_action_ids_and_digest(self):
        args = dict(principal=self.principal, preview=self.preview(),
                    destination_instance="instance-b", plan_id="plan-001")
        self.assertEqual(build_sync_plan(**args), build_sync_plan(**args))

    def test_actor_must_match_authenticated_principal(self):
        preview = self.preview()
        preview["actor"] = "other-agent"
        with self.assertRaises(SyncProtocolError):
            build_sync_plan(principal=self.principal, preview=preview,
                            destination_instance="instance-b", plan_id="plan-001")

    def test_conflicts_are_never_converted_to_actions(self):
        changed = {**self.memory, "content": "Version divergente"}
        preview = self.preview(remote_memory=[changed])
        plan = build_sync_plan(principal=self.principal, preview=preview,
                               destination_instance="instance-b", plan_id="plan-001")
        self.assertEqual(plan["actions"], [])
        self.assertTrue(plan["conflicts_block_execution"])
        self.assertEqual(plan["conflict_count"], 1)

    def test_identical_records_do_not_create_actions(self):
        preview = self.preview(remote_memory=[self.memory], remote_messages=[self.message])
        plan = build_sync_plan(principal=self.principal, preview=preview,
                               destination_instance="instance-b", plan_id="plan-001")
        self.assertEqual(plan["actions"], [])
        self.assertFalse(plan["requires_human_approval"])

    def test_duplicate_resource_across_buckets_is_rejected(self):
        preview = self.preview()
        preview["memory"]["identical"] = [{"type": "memory", "record_id": "MEM-1"}]
        preview["counts"]["identical"] = 1
        with self.assertRaises(SyncProtocolError):
            build_sync_plan(principal=self.principal, preview=preview,
                            destination_instance="instance-b", plan_id="plan-001")

    def test_invalid_limits_and_identifiers_are_rejected(self):
        preview = self.preview()
        for kwargs in (
            {"destination_instance": "../remote"},
            {"plan_id": ""},
            {"max_actions": 0},
            {"max_actions": True},
        ):
            args = {"principal": self.principal, "preview": preview,
                    "destination_instance": "instance-b", "plan_id": "plan-001"}
            args.update(kwargs)
            with self.assertRaises(SyncProtocolError):
                build_sync_plan(**args)

    def test_action_limit_is_enforced(self):
        preview = self.preview()
        with self.assertRaises(SyncProtocolError):
            build_sync_plan(principal=self.principal, preview=preview,
                            destination_instance="instance-b", plan_id="plan-001",
                            max_actions=1)

    def test_tampered_plan_fails_integrity_check(self):
        plan = build_sync_plan(principal=self.principal, preview=self.preview(),
                               destination_instance="instance-b", plan_id="plan-001")
        plan["actions"][0]["status"] = "approved"
        with self.assertRaises(SyncProtocolError):
            validate_plan_integrity(plan)

    def test_execution_flags_cannot_be_enabled(self):
        plan = build_sync_plan(principal=self.principal, preview=self.preview(),
                               destination_instance="instance-b", plan_id="plan-001")
        plan["execution_enabled"] = True
        with self.assertRaises(SyncProtocolError):
            validate_plan_integrity(plan)

    def test_readiness_metadata_is_bound_to_plan_digest(self):
        plan = build_sync_plan(principal=self.principal, preview=self.preview(),
                               destination_instance="instance-b", plan_id="plan-001")
        plan["readiness_blockers"] = []
        with self.assertRaises(SyncProtocolError):
            validate_plan_integrity(plan)

    def test_malformed_action_structure_is_rejected(self):
        plan = build_sync_plan(principal=self.principal, preview=self.preview(),
                               destination_instance="instance-b", plan_id="plan-001")
        plan["actions"][0]["status"] = "approved"
        # Recompute the public digest to prove schema validation is independent
        # from the integrity check and cannot be bypassed by re-hashing.
        import hashlib
        import json
        unsigned = {key: value for key, value in plan.items() if key != "plan_digest"}
        plan["plan_digest"] = hashlib.sha256(json.dumps(
            unsigned, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False
        ).encode("utf-8")).hexdigest()
        with self.assertRaises(SyncProtocolError):
            validate_plan_integrity(plan)


if __name__ == "__main__":
    unittest.main()
