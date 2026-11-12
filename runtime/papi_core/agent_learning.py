"""Analyse factuelle des erreurs et recommandations d'apprentissage, sans auto-modification."""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any
from .audit import AuditError, validate_event

FAILURE_STATUSES = {"blocked", "failed"}
SUCCESS_STATUSES = {"done", "completed"}
MIN_COMPARABLE_SAMPLES = 3
SUPPORTED_ACTIONS = {"task.status_changed", "quality.reviewed", "incident.reported"}

class AgentLearningError(ValueError):
    """Données d'apprentissage invalides."""

def _time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise AgentLearningError("Date d'événement invalide.")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AgentLearningError("Date d'événement invalide.") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise AgentLearningError("La date doit inclure un fuseau horaire.")
    return result.astimezone(timezone.utc)

def build_agent_learning(agents: dict[str, dict[str, Any]], events: list[dict[str, Any]],
                         tasks: list[dict[str, Any]], *, as_of: str | None = None,
                         minimum_samples: int = MIN_COMPARABLE_SAMPLES) -> dict[str, Any]:
    """Produit des constats et pistes à partir d'événements explicites uniquement."""
    if not isinstance(agents, dict) or not isinstance(events, list) or not isinstance(tasks, list):
        raise AgentLearningError("agents, events et tasks doivent être un objet et deux listes.")
    if not isinstance(minimum_samples, int) or isinstance(minimum_samples, bool) or minimum_samples < 3:
        raise AgentLearningError("minimum_samples doit être un entier supérieur ou égal à 3.")
    cutoff = _time(as_of) if as_of is not None else datetime.now(timezone.utc)
    task_map = {}
    for task in tasks:
        if not isinstance(task, dict) or not isinstance(task.get("id"), str) or task["id"] in task_map:
            raise AgentLearningError("Registre de tâches invalide ou identifiant dupliqué.")
        task_map[task["id"]] = task
    seen, rejected = set(), 0
    records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        try:
            validate_event(event)
            if event["event_id"] in seen:
                raise AgentLearningError("Identifiant d'événement dupliqué.")
            seen.add(event["event_id"])
            moment = _time(event["occurred_at"])
            if moment > cutoff or event["action"] not in SUPPORTED_ACTIONS:
                continue
            action, details, agent_id = event["action"], event["details"], event["actor"]
            if agent_id not in agents:
                continue
            category, outcome = None, None
            task_id = event["entity_id"]
            task = task_map.get(task_id, {})
            task_type = task.get("type", task.get("category", "unspecified"))
            if not isinstance(task_type, str) or not task_type.strip():
                task_type = "unspecified"
            if action == "task.status_changed":
                if event["entity_type"] != "task":
                    continue
                outcome = details.get("to_status")
                if outcome not in FAILURE_STATUSES | SUCCESS_STATUSES:
                    continue
                category = "task:" + task_type[:80]
            elif action == "quality.reviewed":
                outcome = details.get("result")
                if outcome not in {"pass", "fail", "rework_required"}:
                    continue
                category = "quality:" + task_type[:80]
            else:
                if details.get("agent_id") != agent_id or details.get("severity") not in {"warning", "critical"}:
                    continue
                outcome, category = "failed", "incident:" + str(details.get("category", "unspecified"))[:80]
            records[agent_id].append({"event_id": event["event_id"], "occurred_at": moment.isoformat(),
                                      "category": category, "outcome": outcome, "task_id": task_id})
        except (AuditError, AgentLearningError, TypeError, KeyError):
            rejected += 1

    reports, comparable = {}, defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for agent_id in sorted(agents):
        agent = agents[agent_id]
        if not isinstance(agent, dict) or agent.get("id", agent_id) != agent_id:
            raise AgentLearningError("Fiche agent incohérente.")
        own = sorted(records.get(agent_id, []), key=lambda x: (x["occurred_at"], x["event_id"]))
        by_category: dict[str, Counter] = defaultdict(Counter)
        for item in own:
            by_category[item["category"]][item["outcome"]] += 1
            if item["outcome"] in FAILURE_STATUSES | {"fail", "rework_required"}:
                comparable[item["category"]][agent_id][1] += 1
            elif item["outcome"] in SUCCESS_STATUSES | {"pass"}:
                comparable[item["category"]][agent_id][0] += 1
        findings = []
        for category in sorted(by_category):
            counts = by_category[category]
            failures = sum(counts[k] for k in FAILURE_STATUSES | {"fail", "rework_required"})
            successes = sum(counts[k] for k in SUCCESS_STATUSES | {"pass"})
            if failures:
                findings.append({"category": category, "finding": "recorded_failure_or_rework",
                    "failures": failures, "successful_outcomes": successes,
                    "sample_size": failures + successes, "evidence_level": "observed",
                    "recommendation": "Analyser les événements sources et proposer une checklist ou une validation supplémentaire.",
                    "evidence_event_ids": [x["event_id"] for x in own if x["category"] == category and x["outcome"] in FAILURE_STATUSES | {"fail", "rework_required"}]})
        status = "insufficient_evidence" if len(own) < minimum_samples else "diagnostic_available"
        reports[agent_id] = {"agent_id": agent_id, "name": agent.get("name"),
            "registry_status": agent.get("status", "unknown"), "status": status,
            "observations": len(own), "findings": findings if status == "diagnostic_available" else [],
            "provisional_findings": findings if status == "insufficient_evidence" else [],
            "evidence_event_ids": [x["event_id"] for x in own], "read_only": True}
    comparisons = []
    for category in sorted(comparable):
        eligible = []
        for agent_id, (successes, failures) in sorted(comparable[category].items()):
            sample = successes + failures
            if sample >= minimum_samples:
                eligible.append({"agent_id": agent_id, "sample_size": sample, "successes": successes, "failures": failures})
        if len(eligible) >= 2:
            comparisons.append({"category": category, "status": "comparable_evidence", "agents": eligible,
                "interpretation": "Descriptif uniquement ; les échantillons ne prouvent ni causalité ni compétence générale."})
    return {"status": "available" if events else "no_events", "source": "explicit_append_only_audit_events",
        "as_of": cutoff.isoformat().replace("+00:00", "Z"), "minimum_samples": minimum_samples,
        "by_agent": reports, "comparisons": comparisons, "rejected_events": rejected,
        "controls": {"automatic_training": False, "agent_behavior_changed": False,
            "identity_or_permissions_changed": False, "memory_written": False,
            "tasks_or_workflows_changed": False, "actions_executed": 0,
            "subjective_scores_generated": False}, "read_only": True}
