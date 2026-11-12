"""Détection explicable des missions à risque; analyse strictement en lecture seule."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

OPEN_STATUSES = {"backlog", "ready", "in_progress", "blocked", "review"}
PRIORITY_WEIGHT = {"low": 1, "normal": 2, "high": 3, "urgent": 4}


class SupervisionError(ValueError):
    """Données ou seuils de supervision invalides."""


def _date(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise SupervisionError(f"{field} doit être une date ISO 8601.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SupervisionError(f"{field} doit être une date ISO 8601.") from exc
    if parsed.tzinfo is None:
        raise SupervisionError(f"{field} doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)


def supervise_tasks(
    tasks: list[dict[str, Any]],
    *,
    agents: dict[str, dict[str, Any]],
    as_of: str,
    due_soon_hours: int = 24,
    stale_after_hours: int = 48,
) -> dict[str, Any]:
    """Classe les tâches ouvertes selon des règles fixes et des seuils explicites.

    Le score est un indicateur de tri, pas une probabilité statistique.
    Aucun agent n'est contacté et aucune tâche n'est modifiée.
    """
    if not isinstance(tasks, list) or not isinstance(agents, dict):
        raise SupervisionError("tasks doit être une liste et agents un objet.")
    if (not isinstance(due_soon_hours, int) or isinstance(due_soon_hours, bool)
            or due_soon_hours < 0 or not isinstance(stale_after_hours, int)
            or isinstance(stale_after_hours, bool) or stale_after_hours < 1):
        raise SupervisionError("Seuils temporels invalides.")
    now = _date(as_of, "as_of")
    due_window = now + timedelta(hours=due_soon_hours)
    stale_before = now - timedelta(hours=stale_after_hours)
    risks: list[dict[str, Any]] = []
    ignored_terminal = 0
    seen: set[str] = set()

    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise SupervisionError(f"Tâche #{index + 1} invalide.")
        status = task.get("status")
        if status in {"done", "cancelled"}:
            ignored_terminal += 1
            continue
        if status not in OPEN_STATUSES:
            raise SupervisionError(f"Statut invalide pour la tâche #{index + 1}.")
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id.strip() or task_id in seen:
            raise SupervisionError(f"Identifiant absent ou dupliqué à la tâche #{index + 1}.")
        seen.add(task_id)
        owner = task.get("owner_agent")
        owner_valid = isinstance(owner, str) and owner in agents
        priority = task.get("priority", "normal")
        if priority not in PRIORITY_WEIGHT:
            raise SupervisionError(f"Priorité invalide pour {task_id}.")

        reasons: list[str] = []
        score = 0
        severity = "low"
        due = _date(task["due_at"], f"due_at de {task_id}") if task.get("due_at") is not None else None
        updated = _date(task["updated_at"], f"updated_at de {task_id}") if task.get("updated_at") is not None else None
        created = _date(task["created_at"], f"created_at de {task_id}") if task.get("created_at") is not None else None

        if status == "blocked":
            score += 45
            reasons.append("mission bloquée (+45)")
        if not owner_valid:
            score += 35
            reasons.append("responsable absent ou inconnu (+35)")
        if due is not None and due < now:
            score += 40
            reasons.append("échéance dépassée (+40)")
        elif due is not None and due <= due_window:
            score += 20
            reasons.append("échéance proche (+20)")
        reference_date = updated or created
        if reference_date is not None and reference_date < stale_before:
            score += 20
            reasons.append("aucune mise à jour récente (+20)")
        if task.get("approval_required") is True and task.get("approval_status") != "approved":
            score += 15
            reasons.append("approbation en attente (+15)")
        if priority in {"high", "urgent"}:
            score += 10 if priority == "high" else 15
            reasons.append(f"priorité {priority} (+{10 if priority == 'high' else 15})")

        if score >= 70:
            severity = "critical"
        elif score >= 40:
            severity = "high"
        elif score >= 20:
            severity = "medium"
        if reasons:
            risks.append({
                "task_id": task_id,
                "title": task.get("title", ""),
                "owner_agent": owner if owner_valid else None,
                "status": status,
                "priority": priority,
                "risk_score": score,
                "severity": severity,
                "reasons": reasons,
            })

    risks.sort(key=lambda item: (
        {"critical": 0, "high": 1, "medium": 2, "low": 3}[item["severity"]],
        -item["risk_score"], item["task_id"],
    ))
    counts = {level: sum(item["severity"] == level for item in risks)
              for level in ("critical", "high", "medium", "low")}
    return {
        "mode": "read_only_proactive_supervision",
        "as_of": now.isoformat().replace("+00:00", "Z"),
        "thresholds": {
            "due_soon_hours": due_soon_hours,
            "stale_after_hours": stale_after_hours,
        },
        "summary": {
            "open_tasks_reviewed": len(tasks) - ignored_terminal,
            "at_risk_tasks": len(risks),
            "by_severity": counts,
            "terminal_tasks_ignored": ignored_terminal,
        },
        "risks": risks,
        "recommended_next_steps": [
            {"task_id": item["task_id"], "action": (
                "escalade humaine prioritaire" if item["severity"] in {"critical", "high"}
                else "revue de suivi"
            )} for item in risks
        ],
        "limitations": [
            "Le score est une règle de tri explicable, pas une probabilité ni une prédiction IA.",
            "Les champs updated_at et created_at sont facultatifs; leur absence ne prouve pas une inactivité.",
            "L'analyse utilise uniquement les données transmises et l'instant as_of.",
            "Aucune notification, affectation, écriture ou action externe n'est effectuée.",
        ],
    }
