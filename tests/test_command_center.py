import json
import tempfile
import unittest
from pathlib import Path
from papi_core.command_center import build_command_center
from papi_core.workers_inputs import WorkersInputError, build_workers_inputs

class WorkersInputAdapterTests(unittest.TestCase):
    def test_adapts_module_outputs_and_marks_sources(self):
        result = build_workers_inputs(
            platform_discovery_batch={"results": [{"platform_id": "p1"}]},
            handoff_records=[{"handoff_id": "h1"}],
            profitability_batch={"results": [{"offer_id": "o1"}]},
        )
        self.assertEqual(result["platform_candidates"][0]["platform_id"], "p1")
        self.assertEqual(result["handoffs"][0]["handoff_id"], "h1")
        self.assertEqual(result["profitability_results"][0]["offer_id"], "o1")
        self.assertTrue(result["sources"]["platform_discovery_supplied"])
        self.assertFalse(result["sources"]["automatic_collection_performed"])
        self.assertFalse(result["sources"]["persistent_storage_read"])
        self.assertFalse(result["sources"]["network_access_performed"])

    def test_absent_source_differs_from_explicit_empty_source(self):
        self.assertFalse(build_workers_inputs()["sources"]["platform_discovery_supplied"])
        empty = build_workers_inputs(platform_discovery_batch={"results": []})
        self.assertTrue(empty["sources"]["platform_discovery_supplied"])
        self.assertEqual(empty["platform_candidates"], [])

    def test_invalid_shapes_are_rejected(self):
        with self.assertRaises(WorkersInputError):
            build_workers_inputs(platform_discovery_batch={"items": []})
        with self.assertRaises(WorkersInputError):
            build_workers_inputs(profitability_batch={"results": ["bad"]})
        with self.assertRaises(WorkersInputError):
            build_workers_inputs(handoff_records={"handoff_id": "h1"})

    def test_empty_results_are_valid(self):
        result = build_workers_inputs(platform_discovery_batch={"results": []}, handoff_records=[], profitability_batch={"results": []})
        self.assertEqual(result["platform_candidates"], [])
        self.assertEqual(result["handoffs"], [])
        self.assertEqual(result["profitability_results"], [])

class CommandCenterTests(unittest.TestCase):
    def _fixtures(self, root):
        agents, tasks, policy = root / "agents.json", root / "tasks.json", root / "policy.json"
        agents.write_text(json.dumps({"agents": [{"id": "astou", "name": "Astou", "status": "defined"},
                                                 {"id": "mariama", "name": "Mariama", "status": "planned"}]}), encoding="utf-8")
        tasks.write_text(json.dumps({"tasks": [{"id": "T-1", "title": "Audit", "status": "ready", "approval_required": True, "approval_status": "pending", "owner_agent": "astou"},
                                               {"id": "T-2", "title": "Research", "status": "backlog", "approval_required": False, "owner_agent": "unknown"}]}), encoding="utf-8")
        policy.write_text(json.dumps({"execution_enabled": False, "external_actions_enabled": False}), encoding="utf-8")
        return tasks, agents, policy

    def test_dashboard_is_read_only_and_safe_when_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            tasks, agents, policy = self._fixtures(Path(directory))
            result = build_command_center(tasks, agents, policy, {})
        self.assertEqual(result["dashboard"]["agents_total"], 2)
        self.assertEqual(result["dashboard"]["tasks_total"], 2)
        self.assertEqual(result["dashboard"]["open_tasks"], 2)
        self.assertEqual(result["dashboard"]["pending_approvals"], 1)
        self.assertEqual(result["dashboard"]["unassigned_open_tasks"], 1)
        self.assertEqual(result["mode"], "read_only_local")
        self.assertFalse(result["controls"]["worker_started"])
        self.assertFalse(result["controls"]["external_actions_enabled"])
        self.assertFalse(result["environment"]["secrets_displayed"])
        self.assertEqual(result["ai_workers"]["platforms"]["total"], 0)
        self.assertFalse(result["ai_workers_sources"]["automatic_collection_performed"])

    def test_normalized_data_remains_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            tasks, agents, policy = self._fixtures(Path(directory))
            result = build_command_center(tasks, agents, policy, {},
                platform_candidates=[{"platform_id": "P1", "name": "Example", "url": "https://example.org", "status": "needs_human_review"}],
                handoffs=[{"handoff_id": "H1", "platform_name": "Example", "required_user_action": "Review", "status": "awaiting_user"}],
                profitability_results=[{"offer_id": "O1", "currency": "XOF", "estimated_net_profit_after_labor": "5000.00", "estimated_net_hourly_rate": "1000.00", "estimated_net_margin_percent": "20.00", "status": "viable_for_human_review"}])
        self.assertEqual(result["ai_workers"]["platforms"]["total"], 1)
        self.assertEqual(result["ai_workers"]["human_handoffs"]["awaiting_user_count"], 1)
        self.assertEqual(result["ai_workers"]["profitability"]["total"], 1)

    def test_command_center_consumes_actual_module_output_shapes(self):
        with tempfile.TemporaryDirectory() as directory:
            tasks, agents, policy = self._fixtures(Path(directory))
            result = build_command_center(tasks, agents, policy, {},
                platform_discovery_batch={"results": [{"platform_id": "p1", "name": "Platform", "url": "https://example.org", "status": "needs_human_review"}]},
                handoff_records=[{"handoff_id": "h1", "status": "awaiting_user"}],
                profitability_batch={"results": [{"offer_id": "o1", "currency": "XOF", "estimated_net_profit_after_labor": "5000.00", "estimated_net_hourly_rate": "1000.00", "estimated_net_margin_percent": "20.00", "status": "viable_for_human_review"}]})
        self.assertEqual(result["ai_workers"]["platforms"]["total"], 1)
        self.assertEqual(result["ai_workers"]["human_handoffs"]["awaiting_user_count"], 1)
        self.assertEqual(result["ai_workers"]["profitability"]["total"], 1)
        self.assertTrue(result["ai_workers_sources"]["profitability_supplied"])
        self.assertFalse(result["ai_workers_sources"]["automatic_collection_performed"])
        self.assertFalse(result["controls"]["worker_started"])
        self.assertFalse(result["controls"]["external_actions_enabled"])

    def test_conflicting_raw_and_wrapped_inputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            tasks, agents, policy = self._fixtures(Path(directory))
            with self.assertRaises(ValueError):
                build_command_center(tasks, agents, policy, {}, platform_candidates=[], platform_discovery_batch={"results": []})

    def test_invalid_task_collection_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agents, tasks = root / "agents.json", root / "tasks.json"
            agents.write_text(json.dumps({"agents": [{"id": "astou", "name": "Astou"}]}), encoding="utf-8")
            tasks.write_text(json.dumps({"tasks": None}), encoding="utf-8")
            with self.assertRaises(ValueError):
                build_command_center(tasks, agents)

    def test_invalid_workers_collection_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            tasks, agents, policy = self._fixtures(Path(directory))
            with self.assertRaises(ValueError):
                build_command_center(tasks, agents, policy, {}, handoffs={"invalid": True})


    def test_command_center_reads_central_store_only_when_injected(self):
        class FakeCentralStore:
            def __init__(self):
                self.called = False

            def load_worker_inputs(self):
                self.called = True
                return {
                    "platform_candidates": [{"platform_id": "P-C", "status": "needs_human_review"}],
                    "handoffs": [{"handoff_id": "H-C", "status": "awaiting_user"}],
                    "profitability_results": [{"offer_id": "O-C", "status": "viable_for_human_review"}],
                }

        with tempfile.TemporaryDirectory() as directory:
            tasks, agents, policy = self._fixtures(Path(directory))
            central = FakeCentralStore()
            result = build_command_center(tasks, agents, policy, {}, worker_store=central)
        self.assertTrue(central.called)
        self.assertEqual(result["mode"], "read_only_supabase")
        self.assertEqual(result["ai_workers"]["platforms"]["total"], 1)
        self.assertEqual(result["ai_workers"]["human_handoffs"]["awaiting_user_count"], 1)
        self.assertTrue(result["ai_workers_sources"]["central_store_read"])
        self.assertTrue(result["ai_workers_sources"]["network_access_performed"])
        self.assertTrue(result["controls"]["storage_reads_performed"])
        self.assertFalse(result["controls"]["writes_performed"])
        self.assertFalse(result["controls"]["worker_started"])

    def test_command_center_rejects_mixing_central_and_explicit_worker_data(self):
        class FakeCentralStore:
            def load_worker_inputs(self):
                return {"platform_candidates": [], "handoffs": [], "profitability_results": []}

        with tempfile.TemporaryDirectory() as directory:
            tasks, agents, policy = self._fixtures(Path(directory))
            with self.assertRaises(ValueError):
                build_command_center(tasks, agents, policy, {}, worker_store=FakeCentralStore(), handoffs=[])

if __name__ == "__main__":
    unittest.main()
