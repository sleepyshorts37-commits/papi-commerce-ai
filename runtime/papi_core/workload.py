"""Analyse en lecture seule de la charge, des retards et blocages des missions."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

OPEN_STATUSES = {"backlog", "ready", "in_progress", "blocked", "review"}
ACTIVE_STATUSES = {"ready", "in_progress", "review"}


class WorkloadError(ValueError):
    """Instantané de charge invalide."""


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise WorkloadError(f"{field} doit être une date ISO 8601.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WorkloadError(f"{field} doit être une date ISO 8601.") from exc
    if parsed.tzinfo is None:
        raise WorkloadError(f"{field} doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)


def analyze_workload(
    tasks: list[dict[str, Any]],
    *,
    agents: dict[str, dict[str, Any]],
    as_of: str,
    capacity_by_agent: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Construit un instantané déterministe; aucune disponibilité réelle n'est inférée.

    La charge compte les tâches ouvertes affectées. Une capacité n'est comparée
    que si elle est explicitement fournie pour l'agent concerné.
    """
    if not isinstance(tasks, list) or not isinstance(agents, dict):
        raise WorkloadError("tasks doit être une liste et agents un objet.")
    now = _timestamp(as_of, "as_of")
    capacities = capacity_by_agent or {}
    if not isinstance(capacities, dict):
        raise WorkloadError("capacity_by_agent doit être un objet.")
    for agent_id, capacity in capacities.items():
        if (agent_id not in agents or not isinstance(capacity, int)
                or isinstance(capacity, bool) or capacity < 0):
            raise WorkloadError("Capacité invalide : agent inconnu ou entier négatif attendu.")

    counts = Counter()
    by_agent: dict[str, dict[str, Any]] = {
        agent_id: {
            "agent_id": agent_id,
            "agent_name": agent.get("name", agent_id),
            "agent_status": agent.get("status", "unknown"),
            "open_tasks": 0,
            "active_tasks": 0,
            "blocked_tasks": 0,
            "overdue_tasks": 0,
            "capacity": capacities.get(agent_id),
            "capacity_state": "unknown" if agent_id not in capacities else "within_capacity",
            "redistribution_recommended": False,
        }
        for agent_id, agent in agents.items()
    }
    overdue: list[dict[str, str]] = []
    blocked: list[dict[str, str]] = []
    unassigned: list[str] = []
    priority_counts = Counter()

    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise WorkloadError(f"Tâche #{index + 1} invalide : objet attendu.")
        status = task.get("status")
        if status not in OPEN_STATUSES and status not in {"done", "cancelled"}:
            raise WorkloadError(f"Statut invalide pour la tâche #{index + 1}.")
        if status in {"done", "cancelled"}:
            continue
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id.strip():
            raise WorkloadError(f"Tâche #{index + 1} sans identifiant valide.")
        counts[status] += 1
        priority = task.get("priority", "unknown")
        if not isinstance(priority, str):
            raise WorkloadError(f"Priorité invalide pour {task_id}.")
        priority_counts[priority] += 1
        owner = task.get("owner_agent")
        if not isinstance(owner, str) or owner not in agents:
            unassigned.append(task_id)
        else:
            row = by_agent[owner]
            row["open_tasks"] += 1
            if status in ACTIVE_STATUSES:
                row["active_tasks"] += 1
            if status == "blocked":
                row["blocked_tasks"] += 1
        if status == "blocked":
            blocked.append({"task_id": task_id, "owner_agent": owner if isinstance(owner, str) else ""})
        due_at = task.get("due_at")
        if due_at is not None:
            due = _timestamp(due_at, f"due_at de {task_id}")
            if due < now:
                overdue.append({"task_id": task_id, "owner_agent": owner if isinstance(owner, str) else ""})

    overloaded: list[str] = []
    for agent_id, row in by_agent.items():
        if agent_id in capacities:
            if row["open_tasks"] > row["capacity"]:
                row["capacity_state"] = "over_capacity"
                row["redistribution_recommended"] = True
                overloaded.append(agent_id)
            else:
                row["capacity_state"] = "within_capacity"

    recommendations = []
    if overdue:
        recommendations.append("Examiner les échéances dépassées et réviser les priorités.")
    if blocked:
        recommendations.append("Faire analyser les tâches bloquées et leurs dépendances.")
    if unassigned:
        recommendations.append("Faire attribuer les tâches sans responsable valide.")
    if overloaded:
        recommendations.append("Étudier une redistribution contrôlée pour les agents au-delà de leur capacité déclarée.")
    if not recommendations:
        recommendations.append("Aucune alerte détectée dans cet instantané; poursuivre le suivi des échéances.")

    return {
        "mode": "read_only_workload_snapshot",
        "as_of": now.isoformat().replace("+00:00", "Z"),
        "summary": {
            "open_tasks": sum(counts.values()),
            "by_status": dict(sorted(counts.items())),
            "by_priority": dict(sorted(priority_counts.items())),
            "overdue_count": len(overdue),
            "blocked_count": len(blocked),
            "unassigned_count": len(unassigned),
            "over_capacity_agents": overloaded,
        },
        "agents": by_agent,
        "overdue_tasks": overdue,
        "blocked_tasks": blocked,
        "unassigned_tasks": unassigned,
        "recommendations": recommendations,
        "limitations": [
            "La charge mesure les tâches ouvertes enregistrées, pas le temps de travail réel.",
            "Une capacité absente reste inconnue; aucune capacité par défaut n'est inventée.",
            "Les échéances sont comparées à as_of; aucune horloge ni source externe n'est consultée.",
            "Aucune réaffectation, écriture, notification ou exécution n'est effectuée.",
        ],
    }
