import copy
import unittest

from runtime.papi_core.agent_workflows import (
    AgentWorkflowError, build_workflow_candidate, build_workflow_center,
)


def fixture():
    ids = []
    agents = {}
    for agent_id, permissions in (("owner", ["create_agent_workflows"]),
                                  ("worker", []), ("reviewer", [])):
        identity = {
            "identity_id": "PAPI-ID-" + agent_id.upper(), "agent_id": agent_id,
            "full_name": agent_id, "role": "test", "department": "test",
            "manager_id": None, "mission": "test", "competencies": ["test"],
            "objectives": ["test"], "autonomy_level": "limited",
            "permissions": permissions, "prohibited_actions": [],
            "status": "active", "created_at": "2026-01-01T00:00:00Z",
            "assignment_history": [], "evaluation_history": [],
            "profile_state": "complete",
        }
        ids.append(identity)
        agents[agent_id] = {"id": agent_id, "status": "active"}
    steps = [
        {"step_id": "step-a", "title": "Recherche", "instructions": "Analyser",
         "assignee_id": "worker", "depends_on": [], "acceptance_criteria": ["Sources vérifiées"],
         "reviewer_id": "reviewer", "approval_required": True},
        {"step_id": "step-b", "title": "Rapport", "instructions": "Rédiger",
         "assignee_id": "worker", "depends_on": ["step-a"], "acceptance_criteria": ["Rapport complet"],
         "reviewer_id": "reviewer", "approval_required": True},
    ]
    return {"identities": ids}, agents, steps


def candidate():
    identities, agents, steps = fixture()
    return build_workflow_candidate(
        workflow_id="wf-001", name="Étude", description="Étude commerciale",
        creator_id="owner", priority="normal", created_at="2026-11-12T10:00:00Z",
        steps=steps, identity_document=identities, agents=agents,
    )


class AgentWorkflowTests(unittest.TestCase):
    def test_valid_dag_is_only_a_candidate(self):
        result = candidate()
        self.assertEqual(result["workflow"]["topological_order"], ["step-a", "step-b"])
        self.assertFalse(result["workflow_persisted"])
        self.assertEqual(result["workers_started"], 0)

    def test_missing_dependency_rejected(self):
        identities, agents, steps = fixture()
        steps[1]["depends_on"] = ["missing"]
        with self.assertRaises(AgentWorkflowError):
            build_workflow_candidate(workflow_id="wf-002", name="Étude", description="Détail",
                creator_id="owner", priority="normal", created_at="2026-11-12T10:00:00Z",
                steps=steps, identity_document=identities, agents=agents)

    def test_cycle_rejected(self):
        identities, agents, steps = fixture()
        steps[0]["depends_on"] = ["step-b"]
        with self.assertRaises(AgentWorkflowError):
            build_workflow_candidate(workflow_id="wf-003", name="Étude", description="Détail",
                creator_id="owner", priority="normal", created_at="2026-11-12T10:00:00Z",
                steps=steps, identity_document=identities, agents=agents)

    def test_unpermitted_creator_rejected(self):
        identities, agents, steps = fixture()
        identities["identities"][0]["permissions"] = []
        with self.assertRaises(AgentWorkflowError):
            build_workflow_candidate(workflow_id="wf-004", name="Étude", description="Détail",
                creator_id="owner", priority="normal", created_at="2026-11-12T10:00:00Z",
                steps=steps, identity_document=identities, agents=agents)

    def test_incomplete_assignee_rejected(self):
        identities, agents, steps = fixture()
        identities["identities"][1]["profile_state"] = "incomplete"
        with self.assertRaises(AgentWorkflowError):
            build_workflow_candidate(workflow_id="wf-005", name="Étude", description="Détail",
                creator_id="owner", priority="normal", created_at="2026-11-12T10:00:00Z",
                steps=steps, identity_document=identities, agents=agents)

    def test_duplicate_step_rejected(self):
        identities, agents, steps = fixture()
        steps[1]["step_id"] = "step-a"
        with self.assertRaises(AgentWorkflowError):
            build_workflow_candidate(workflow_id="wf-006", name="Étude", description="Détail",
                creator_id="owner", priority="normal", created_at="2026-11-12T10:00:00Z",
                steps=steps, identity_document=identities, agents=agents)

    def test_quality_gate_requires_evidence_and_distinct_reviewer(self):
        result = candidate()
        gate = result["workflow"]["steps"][0]["quality_gate"]
        self.assertTrue(gate["evidence_required"])
        self.assertFalse(gate["pass_without_evidence"])
        identities, agents, steps = fixture()
        steps[0]["reviewer_id"] = "worker"
        with self.assertRaises(AgentWorkflowError):
            build_workflow_candidate(workflow_id="wf-007", name="Étude", description="Détail",
                creator_id="owner", priority="normal", created_at="2026-11-12T10:00:00Z",
                steps=steps, identity_document=identities, agents=agents)

    def test_center_empty_and_read_only(self):
        identities, agents, _ = fixture()
        center = build_workflow_center([], identities, agents)
        self.assertEqual(center["workflow_count"], 0)
        self.assertEqual(center["workers_started"], 0)
        self.assertTrue(center["read_only"])

    def test_event_projection_rejects_duplicate(self):
        identities, agents, _ = fixture()
        result = candidate()["workflow"]
        event = {"event_id": "WORKFLOW-EVENT-wf-001", "occurred_at": "2026-11-12T10:00:00Z",
                 "actor": "owner", "action": "agent.workflow.proposed",
                 "entity_type": "agent_workflow", "entity_id": "wf-001", "details": result}
        center = build_workflow_center([event, copy.deepcopy(event)], identities, agents)
        self.assertEqual(center["workflow_count"], 1)
        self.assertEqual(center["rejected_events"], 1)


if __name__ == "__main__":
    unittest.main()
