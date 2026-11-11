import json
import tempfile
import unittest
from pathlib import Path

from papi_core.registry import load_agents, validate_task, validate_registries
from papi_core.audit import AuditError, append_event, new_event, read_events
from papi_core.orchestrator import build_dispatch_plan
from papi_core.state_machine import TransitionError, approve_task, transition_task
from papi_core.storage import StoreError, SupabaseStore


class RegistryTests(unittest.TestCase):
    def test_committed_registries_are_valid(self):
        self.assertEqual(validate_registries(), [])

    def test_unknown_agent_is_rejected(self):
        task = {
            "id": "PAPI-TEST-001", "title": "Test", "department": "Test",
            "owner_agent": "agent-inexistant", "status": "backlog",
            "priority": "normal", "created_at": "2026-11-11T00:00:00Z",
            "approval_required": False
        }
        errors = validate_task(task, load_agents())
        self.assertTrue(any("Agent inconnu" in error for error in errors))

    def test_unapproved_task_cannot_start(self):
        task = {
            "id": "PAPI-TEST-002", "title": "Test", "department": "Test",
            "owner_agent": "astou", "status": "in_progress",
            "priority": "normal", "created_at": "2026-11-11T00:00:00Z",
            "approval_required": True, "approval_status": "pending"
        }
        errors = validate_task(task, load_agents())
        self.assertTrue(any("sans approbation" in error for error in errors))

    def test_done_task_requires_evidence(self):
        task = {
            "id": "PAPI-TEST-003", "title": "Test", "department": "Test",
            "owner_agent": "astou", "status": "done", "priority": "normal",
            "created_at": "2026-11-11T00:00:00Z", "approval_required": False
        }
        errors = validate_task(task, load_agents())
        self.assertTrue(any("preuve" in error for error in errors))

    def test_dispatch_plan_is_proposal_only_and_priority_sorted(self):
        with tempfile.TemporaryDirectory() as directory:
            tasks_path = Path(directory) / "tasks.json"
            tasks_path.write_text(json.dumps({"tasks": [
                {"id": "PAPI-LOW-001", "department": "Prospection", "status": "ready", "priority": "low", "created_at": "2026-11-11"},
                {"id": "PAPI-HIGH-001", "department": "Prospection", "status": "ready", "priority": "high", "created_at": "2026-11-11"}
            ]}), encoding="utf-8")
            plan = build_dispatch_plan(tasks_path)
        self.assertEqual(plan["mode"], "proposal_only")
        self.assertEqual(plan["proposals"][0]["task_id"], "PAPI-HIGH-001")
        self.assertFalse(plan["proposals"][0]["dispatch_allowed"])
        self.assertEqual(plan["proposals"][0]["blocking_reason"], "no_deployed_agent")

    def test_approval_blocks_dispatch_proposal(self):
        with tempfile.TemporaryDirectory() as directory:
            tasks_path = Path(directory) / "tasks.json"
            tasks_path.write_text(json.dumps({"tasks": [
                {"id": "PAPI-APP-001", "department": "Direction", "status": "ready", "priority": "urgent", "approval_required": True, "approval_status": "pending"}
            ]}), encoding="utf-8")
            plan = build_dispatch_plan(tasks_path)
        self.assertEqual(plan["proposals"][0]["blocking_reason"], "approval_required")
        self.assertFalse(plan["proposals"][0]["dispatch_allowed"])


class AuditTests(unittest.TestCase):
    def make_event(self, event_id="EVT-001", details=None):
        return new_event(
            event_id=event_id, actor="astou", action="task.reviewed",
            entity_type="task", entity_id="PAPI-001", details=details or {"decision": "review"}
        )

    def test_append_and_read_audit_event(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            event = self.make_event()
            self.assertTrue(append_event(event, path))
            self.assertEqual(read_events(path), [event])

    def test_duplicate_event_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            event = self.make_event()
            self.assertTrue(append_event(event, path))
            self.assertFalse(append_event(event, path))
            self.assertEqual(len(read_events(path)), 1)

    def test_sensitive_fields_are_rejected(self):
        with self.assertRaises(AuditError):
            self.make_event(details={"access_token": "never-store"})

    def test_corrupt_log_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_text("{broken json}\n", encoding="utf-8")
            with self.assertRaises(AuditError):
                read_events(path)


class StateMachineTests(unittest.TestCase):
    def base_task(self, **changes):
        task = {
            "id": "PAPI-STATE-001", "status": "backlog",
            "approval_required": False, "evidence": []
        }
        task.update(changes)
        return task

    def test_valid_lifecycle_requires_quality_review_and_evidence(self):
        task, event1 = transition_task(self.base_task(), "ready", actor="marietou")
        task, event2 = transition_task(task, "in_progress", actor="astou")
        task, event3 = transition_task(task, "review", actor="astou")
        with self.assertRaises(TransitionError):
            transition_task(task, "done", actor="mariama")
        task, event4 = transition_task(task, "done", actor="mariama", evidence=["https://example.org/result"])
        self.assertEqual(task["status"], "done")
        self.assertEqual(event4["details"]["from_status"], "review")
        self.assertEqual(len({event1["event_id"], event2["event_id"], event3["event_id"], event4["event_id"]}), 4)

    def test_invalid_transition_is_rejected(self):
        with self.assertRaises(TransitionError):
            transition_task(self.base_task(), "done", actor="astou")

    def test_approval_is_required_before_execution(self):
        task = self.base_task(approval_required=True, approval_status="pending")
        with self.assertRaises(TransitionError):
            transition_task(task, "ready", actor="marietou")
        task, event = approve_task(task, approver="owner", decision="approved")
        task, _ = transition_task(task, "ready", actor="marietou")
        task, _ = transition_task(task, "in_progress", actor="astou")
        self.assertEqual(task["status"], "in_progress")
        self.assertEqual(task["approval_status"], "approved")

    def test_approval_decision_cannot_be_overwritten(self):
        task = self.base_task(approval_required=True, approval_status="pending")
        task, _ = approve_task(task, approver="owner", decision="rejected")
        with self.assertRaises(TransitionError):
            approve_task(task, approver="owner", decision="approved")

    def test_cancelled_task_is_terminal(self):
        task, _ = transition_task(self.base_task(), "cancelled", actor="owner")
        with self.assertRaises(TransitionError):
            transition_task(task, "ready", actor="owner")


import unittest
from unittest.mock import patch

from papi_core.storage import StoreError, SupabaseStore


class StorageTests(unittest.TestCase):
    def test_requires_https_and_key(self):
        with self.assertRaises(StoreError):
            SupabaseStore(url="http://example.org", key="x")
        with self.assertRaises(StoreError):
            SupabaseStore(url="https://example.org", key="")

    @patch.dict("os.environ", {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_KEY": "test-key"})
    def test_task_insert_returns_version(self):
        store = SupabaseStore()
        with patch.object(store, "_request", return_value=[{"version": 1}]) as request:
            version = store.save_task({"id": "PAPI-001", "status": "backlog"})
        self.assertEqual(version, 1)
        self.assertEqual(request.call_args.args[0], "POST")

    @patch.dict("os.environ", {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_KEY": "test-key"})
    def test_task_update_uses_optimistic_version(self):
        store = SupabaseStore()
        with patch.object(store, "_request", return_value=[{"version": 3}]) as request:
            version = store.save_task({"id": "PAPI-001", "status": "ready"}, expected_version=2)
        self.assertEqual(version, 3)
        self.assertIn("version=eq.2", request.call_args.args[1])

    @patch.dict("os.environ", {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_KEY": "test-key"})
    def test_concurrent_update_conflict_is_rejected(self):
        store = SupabaseStore()
        with patch.object(store, "_request", return_value=[]):
            with self.assertRaises(StoreError):
                store.save_task({"id": "PAPI-001"}, expected_version=1)


if __name__ == "__main__":
    unittest.main()
