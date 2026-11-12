import copy
import unittest

from runtime.papi_core.agent_memory import (
    AgentMemoryError, build_memory_candidate, build_memory_center, recall_agent_memory,
)


def fixture():
    identity = {
        "identity_id": "PAPI-ID-AGENT-A", "agent_id": "agent-a",
        "full_name": "Agent A", "role": "test", "department": "test",
        "manager_id": None, "mission": "test", "competencies": ["test"],
        "objectives": ["test"], "autonomy_level": "limited",
        "permissions": ["manage_own_memory"], "prohibited_actions": [],
        "status": "active", "created_at": "2026-01-01T00:00:00Z",
        "assignment_history": [], "evaluation_history": [],
        "profile_state": "complete",
    }
    other = {**identity, "identity_id": "PAPI-ID-AGENT-B", "agent_id": "agent-b",
             "full_name": "Agent B"}
    return {"identities": [identity, other]}


def candidate():
    return build_memory_candidate(
        memory_id="mem-001", agent_id="agent-a", category="lesson",
        title="Leçon prospection", content="Vérifier les besoins avant une proposition.",
        tags=["vente", "prospection"], source_ref="task-123", visibility="private",
        created_at="2026-11-12T10:00:00Z", identity_document=fixture(),
    )


class AgentMemoryTests(unittest.TestCase):
    def test_candidate_is_not_persisted(self):
        result = candidate()
        self.assertFalse(result["persisted"])
        self.assertEqual(result["scope_enforced"], "own_agent_memory")

    def test_permission_required(self):
        identities = fixture()
        identities["identities"][0]["permissions"] = []
        with self.assertRaises(AgentMemoryError):
            build_memory_candidate(memory_id="mem-002", agent_id="agent-a",
                category="lesson", title="Leçon", content="Contenu", tags=[],
                source_ref=None, visibility="private",
                created_at="2026-11-12T10:00:00Z", identity_document=identities)

    def test_sensitive_content_rejected(self):
        with self.assertRaises(AgentMemoryError):
            build_memory_candidate(memory_id="mem-003", agent_id="agent-a",
                category="knowledge", title="Accès", content="Mon password est secret",
                tags=[], source_ref=None, visibility="private",
                created_at="2026-11-12T10:00:00Z", identity_document=fixture())

    def test_invalid_category_rejected(self):
        with self.assertRaises(AgentMemoryError):
            build_memory_candidate(memory_id="mem-004", agent_id="agent-a",
                category="unknown", title="Leçon", content="Contenu", tags=[],
                source_ref=None, visibility="private",
                created_at="2026-11-12T10:00:00Z", identity_document=fixture())

    def test_center_projects_recorded_events_only(self):
        result = candidate()["memory"]
        event = {"event_id": "MEMORY-EVENT-mem-001", "occurred_at": result["created_at"],
                 "actor": "agent-a", "action": "agent.memory.recorded",
                 "entity_type": "agent_memory", "entity_id": "mem-001",
                 "details": {k: v for k, v in result.items() if k != "created_at"}}
        center = build_memory_center([event], fixture())
        self.assertEqual(center["entry_count"], 1)
        self.assertEqual(center["entries"][0]["status"], "recorded_memory")

    def test_duplicate_memory_rejected(self):
        result = candidate()["memory"]
        event = {"event_id": "MEMORY-EVENT-mem-001", "occurred_at": result["created_at"],
                 "actor": "agent-a", "action": "agent.memory.recorded",
                 "entity_type": "agent_memory", "entity_id": "mem-001",
                 "details": {k: v for k, v in result.items() if k != "created_at"}}
        center = build_memory_center([event, copy.deepcopy(event)], fixture())
        self.assertEqual(center["entry_count"], 1)
        self.assertEqual(center["rejected_events"], 1)

    def test_private_recall_is_scoped_to_requesting_agent(self):
        result = candidate()["memory"]
        event = {"event_id": "MEMORY-EVENT-mem-001", "occurred_at": result["created_at"],
                 "actor": "agent-a", "action": "agent.memory.recorded",
                 "entity_type": "agent_memory", "entity_id": "mem-001",
                 "details": {k: v for k, v in result.items() if k != "created_at"}}
        center = build_memory_center([event], fixture())
        recall = recall_agent_memory(agent_id="agent-a", query="prospection besoins",
                                     memory_center=center, identity_document=fixture())
        self.assertEqual(recall["result_count"], 1)
        hidden = recall_agent_memory(agent_id="agent-b", query="prospection besoins",
                                     memory_center=center, identity_document=fixture())
        self.assertEqual(hidden["result_count"], 0)
        self.assertFalse(recall["cross_agent_access"])

    def test_non_private_memory_not_returned_by_private_recall(self):
        result = candidate()["memory"]
        result["visibility"] = "team"
        event = {"event_id": "MEMORY-EVENT-mem-001", "occurred_at": result["created_at"],
                 "actor": "agent-a", "action": "agent.memory.recorded",
                 "entity_type": "agent_memory", "entity_id": "mem-001",
                 "details": {k: v for k, v in result.items() if k != "created_at"}}
        center = build_memory_center([event], fixture())
        recall = recall_agent_memory(agent_id="agent-a", query="prospection besoins",
                                     memory_center=center, identity_document=fixture())
        self.assertEqual(recall["result_count"], 0)


if __name__ == "__main__":
    unittest.main()
