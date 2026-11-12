"""Évaluation factuelle et prudente des agents, strictement en lecture seule."""
from __future__ import annotations

from typing import Any

from .agent_history import AgentHistoryError, summarize_agent_history


ACTIVE_STATUSES = {"active", "running", "deployed"}


class AgentPerformanceError(ValueError):
    """Entrées d'évaluation incohérentes."""


def build_agent_performance(
    agents: dict[str, dict[str, Any]],
    events: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Produit des indicateurs traçables sans noter ni piloter les agents.

    Les agents non déployés restent non évaluables, même si leur fiche existe.
    Aucun chiffre d'affaires n'est estimé à partir de tâches ou d'événements
    commerciaux non vérifiés.
    """
    if not isinstance(agents, dict) or not isinstance(events, list) or not isinstance(tasks, list):
        raise AgentPerformanceError("agents, events et tasks doivent être respectivement un objet et deux listes.")
    results: dict[str, Any] = {}
    for agent_id in sorted(agents):
        agent = agents[agent_id]
        if not isinstance(agent, dict) or agent.get("id", agent_id) != agent_id:
            raise AgentPerformanceError(f"Fiche agent incohérente : {agent_id}.")
        try:
            history = summarize_agent_history(agent_id, events, tasks, as_of=as_of)
        except AgentHistoryError as exc:
            raise AgentPerformanceError(str(exc)) from exc
        metrics = history["metrics"]
        assigned = metrics["tasks_assigned"]
        completed = metrics["tasks_completed_by_agent"]
        ratio = None
        ratio_status = "insufficient_evidence"
        if assigned > 0 and completed <= assigned:
            ratio = round(completed / assigned, 4)
            ratio_status = "measured"
        elif completed > assigned:
            ratio_status = "inconsistent_evidence"

        operational = agent.get("status") in ACTIVE_STATUSES
        if not operational:
            evaluation_status = "not_evaluable"
            recommendation = "Agent non déployé/actif selon le registre ; compléter son profil et valider son déploiement avant toute évaluation."
        elif not metrics["recorded_events"]:
            evaluation_status = "insufficient_evidence"
            recommendation = "Collecter un historique de tâches fiable avant de conclure sur la performance."
        else:
            evaluation_status = "measured"
            recommendation = "Examiner les indicateurs et les preuves avec un responsable ; aucune décision automatique."
        results[agent_id] = {
            "agent_id": agent_id,
            "name": agent.get("name"),
            "department": agent.get("department"),
            "registry_status": agent.get("status", "unknown"),
            "evaluation_status": evaluation_status,
            "metrics": {
                "tasks_assigned": assigned,
                "tasks_completed_by_agent": completed,
                "tasks_blocked_by_agent": metrics["tasks_blocked_by_agent"],
                "tasks_cancelled_by_agent": metrics["tasks_cancelled_by_agent"],
                "status_transitions_by_agent": metrics["status_transitions_by_agent"],
                "average_completion_seconds": metrics["average_completion_seconds"],
                "completion_samples": metrics["completion_samples"],
                "recorded_events": metrics["recorded_events"],
                "completion_ratio": ratio,
                "completion_ratio_status": ratio_status,
            },
            "commercial_performance": {
                "status": "not_measured",
                "verified_revenue_xof": None,
                "reason": "Aucune source de paiement vérifiée et autorisée n'est fournie à ce calcul."
            },
            "strengths": [],
            "risks": (["Tâches bloquées observées ; analyser leurs causes."] if metrics["tasks_blocked_by_agent"] else []),
            "recommendation": recommendation,
            "evidence_source": "append_only_audit_events_and_task_registry",
            "read_only": True,
        }

    counts = {
        "agents_total": len(results),
        "agents_measured": sum(1 for item in results.values() if item["evaluation_status"] == "measured"),
        "agents_insufficient_evidence": sum(1 for item in results.values() if item["evaluation_status"] == "insufficient_evidence"),
        "agents_not_evaluable": sum(1 for item in results.values() if item["evaluation_status"] == "not_evaluable"),
    }
    return {
        "status": "available" if events else "no_events",
        "source": "append_only_audit_events_and_task_registry",
        "read_only": True,
        "as_of": as_of,
        "summary": counts,
        "by_agent": results,
        "controls": {
            "scores_generated": False,
            "agent_statuses_changed": 0,
            "permissions_changed": 0,
            "tasks_changed": 0,
            "commercial_revenue_inferred": False,
            "actions_executed": 0,
        },
    }
