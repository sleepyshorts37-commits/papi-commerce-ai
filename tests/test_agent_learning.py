from runtime.papi_core.agent_learning import build_agent_learning, AgentLearningError

def _event(event_id, actor, outcome):
    return {"event_id": event_id, "occurred_at": "2026-11-12T10:00:00Z", "actor": actor,
        "action": "task.status_changed", "entity_type": "task", "entity_id": event_id,
        "details": {"from_status": "in_progress", "to_status": outcome}}

def test_insufficient_evidence_has_no_confirmed_findings():
    agents = {"a": {"id": "a", "name": "A", "status": "planned"}}
    result = build_agent_learning(agents, [_event("e1", "a", "failed")], [])
    assert result["by_agent"]["a"]["status"] == "insufficient_evidence"
    assert result["by_agent"]["a"]["findings"] == []
    assert result["by_agent"]["a"]["provisional_findings"]

def test_three_events_enable_diagnostic_and_keep_evidence():
    agents = {"a": {"id": "a", "name": "A", "status": "planned"}}
    events = [_event("e1", "a", "failed"), _event("e2", "a", "done"), _event("e3", "a", "blocked")]
    report = build_agent_learning(agents, events, [])["by_agent"]["a"]
    assert report["status"] == "diagnostic_available"
    assert report["findings"][0]["failures"] == 2
    assert len(report["findings"][0]["evidence_event_ids"]) == 2

def test_comparison_requires_two_agents_and_three_samples_each():
    agents = {key: {"id": key, "status": "planned"} for key in ("a", "b")}
    events = [_event(f"{agent}{i}", agent, outcome) for agent in ("a", "b")
              for i, outcome in enumerate(("done", "done", "failed"))]
    result = build_agent_learning(agents, events, [])
    assert len(result["comparisons"]) == 1
    assert all(x["sample_size"] == 3 for x in result["comparisons"][0]["agents"])

def test_no_comparison_with_small_sample():
    agents = {key: {"id": key} for key in ("a", "b")}
    assert build_agent_learning(agents, [_event("a1", "a", "failed"), _event("b1", "b", "done")], [])["comparisons"] == []

def test_duplicate_event_id_is_rejected():
    agents = {"a": {"id": "a"}}
    event = _event("dup", "a", "failed")
    assert build_agent_learning(agents, [event, event], [])["rejected_events"] == 1

def test_learning_never_changes_permissions_or_execution():
    agents = {"a": {"id": "a", "status": "planned", "permissions": ["read"]}}
    before = repr(agents)
    result = build_agent_learning(agents, [], [])
    assert repr(agents) == before
    assert result["controls"]["actions_executed"] == 0
    assert result["controls"]["identity_or_permissions_changed"] is False

def test_invalid_minimum_is_rejected():
    try:
        build_agent_learning({}, [], [], minimum_samples=1)
    except AgentLearningError:
        return
    assert False
