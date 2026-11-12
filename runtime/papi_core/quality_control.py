"""Contrôle qualité déterministe des résultats déclarés, strictement en lecture seule."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .audit import AuditError, validate_event

VALID_RESULTS = {"pass", "fail", "rework_required"}
REVIEW_ACTION = "quality.reviewed"


class QualityControlError(ValueError):
    """Données de contrôle qualité invalides."""


def _parse_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise QualityControlError("Date de revue invalide.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QualityControlError("Date de revue invalide.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise QualityControlError("La date de revue doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)


def _safe_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 120:
        raise QualityControlError(f"{field} doit être un identifiant texte non vide.")
    return value.strip()


def build_quality_control(
    tasks: list[dict[str, Any]],
    events: list[dict[str, Any]],
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Projette les revues qualité explicites ; n'inspecte ni ne certifie le contenu des livrables."""
    if not isinstance(tasks, list) or not isinstance(events, list):
        raise QualityControlError("tasks et events doivent être des listes.")
    cutoff = _parse_time(as_of) if as_of is not None else datetime.now(timezone.utc)
    task_map: dict[str, dict[str, Any]] = {}
    for task in tasks:
        if not isinstance(task, dict):
            raise QualityControlError("Fiche tâche invalide.")
        task_id = _safe_id(task.get("id"), "task.id")
        if task_id in task_map:
            raise QualityControlError(f"Tâche dupliquée : {task_id}.")
        task_map[task_id] = task

    seen: set[str] = set()
    latest: dict[str, dict[str, Any]] = {}
    rejected = 0
    for event in events:
        if not isinstance(event, dict) or event.get("action") != REVIEW_ACTION:
            continue
        try:
            validate_event(event)
            event_id = _safe_id(event["event_id"], "event_id")
            if event_id in seen:
                raise QualityControlError("Identifiant d'événement dupliqué.")
            seen.add(event_id)
            if event["entity_type"] != "task" or event["entity_id"] not in task_map:
                raise QualityControlError("La revue ne référence pas une tâche connue.")
            details = event["details"]
            result = details.get("result")
            if result not in VALID_RESULTS:
                raise QualityControlError("Résultat de revue non reconnu.")
            moment = _parse_time(event["occurred_at"])
            if moment > cutoff:
                continue
            criteria_total = details.get("criteria_total")
            criteria_passed = details.get("criteria_passed")
            if criteria_total is not None or criteria_passed is not None:
                if (isinstance(criteria_total, bool) or not isinstance(criteria_total, int)
                    or isinstance(criteria_passed, bool) or not isinstance(criteria_passed, int)
                    or criteria_total < 1 or criteria_passed < 0 or criteria_passed > criteria_total):
                    raise QualityControlError("Compteurs de critères incohérents.")
            reviewer_id = details.get("reviewer_id", event["actor"])
            reviewer_id = _safe_id(reviewer_id, "reviewer_id")
            normalized = {
                "event_id": event_id, "task_id": event["entity_id"],
                "reviewer_id": reviewer_id, "result": result,
                "occurred_at": moment.isoformat().replace("+00:00", "Z"),
                "criteria_total": criteria_total, "criteria_passed": criteria_passed,
                "evidence_ref": details.get("evidence_ref"),
            }
            previous = latest.get(event["entity_id"])
            if previous is None or (moment, event_id) > (previous["_moment"], previous["event_id"]):
                normalized["_moment"] = moment
                latest[event["entity_id"]] = normalized
        except (AuditError, QualityControlError, TypeError, KeyError):
            rejected += 1

    reports = []
    for task_id in sorted(task_map):
        task = task_map[task_id]
        review = latest.get(task_id)
        if review is None:
            status = "awaiting_review" if task.get("status") in {"review", "in_review", "quality_review"} else "not_reviewed"
            reports.append({
                "task_id": task_id, "task_status": task.get("status", "unknown"),
                "quality_status": status, "review": None,
                "findings": ["Aucune revue qualité explicite trouvée."],
                "automatic_action": False,
            })
            continue
        result = review["result"]
        if result == "pass":
            findings, status = [], "review_passed"
        elif result == "fail":
            findings, status = ["Revue explicitement échouée : correction requise avant validation."], "review_failed"
        else:
            findings, status = ["Reprise demandée par le réviseur ; fournir une nouvelle version et une nouvelle revue."], "rework_required"
        reports.append({
            "task_id": task_id, "task_status": task.get("status", "unknown"),
            "quality_status": status,
            "review": {k: v for k, v in review.items() if k != "_moment"},
            "findings": findings, "automatic_action": False,
        })

    counts = {key: sum(item["quality_status"] == key for item in reports)
              for key in ("awaiting_review", "not_reviewed", "review_passed", "review_failed", "rework_required")}
    return {
        "status": "available" if events else "no_review_events",
        "source": "explicit_quality_review_audit_events",
        "tasks_total": len(reports), "summary": counts,
        "reviews_rejected": rejected, "by_task": reports,
        "controls": {
            "read_only": True, "deliverable_content_inspected": False,
            "quality_claims_inferred": False, "tasks_changed": 0,
            "reviews_created": 0, "agents_notified": 0,
            "assignments_changed": 0, "actions_executed": 0,
        },
    }


def build_quality_review_candidate(
    *, task_id: str, reviewer_id: str, review_id: str,
    criteria: list[dict[str, Any]], evidence_ref: str,
    occurred_at: str,
) -> dict[str, Any]:
    """Prépare une revue structurée candidate ; n'écrit aucun événement."""
    task_id = _safe_id(task_id, "task_id")
    reviewer_id = _safe_id(reviewer_id, "reviewer_id")
    review_id = _safe_id(review_id, "review_id")
    evidence_ref = _safe_id(evidence_ref, "evidence_ref")
    moment = _parse_time(occurred_at)
    if not isinstance(criteria, list) or not criteria or len(criteria) > 30:
        raise QualityControlError("La revue exige entre 1 et 30 critères.")
    normalized = []
    seen = set()
    for item in criteria:
        if not isinstance(item, dict) or set(item) != {"criterion_id", "passed"}:
            raise QualityControlError("Chaque critère doit contenir criterion_id et passed.")
        criterion_id = _safe_id(item["criterion_id"], "criterion_id")
        if criterion_id in seen or not isinstance(item["passed"], bool):
            raise QualityControlError("Critère dupliqué ou résultat invalide.")
        seen.add(criterion_id)
        normalized.append({"criterion_id": criterion_id, "passed": item["passed"]})
    passed = sum(item["passed"] for item in normalized)
    result = "pass" if passed == len(normalized) else "rework_required"
    event = {
        "event_id": f"QUALITY-REVIEW-{review_id}",
        "occurred_at": moment.isoformat().replace("+00:00", "Z"),
        "actor": reviewer_id, "action": REVIEW_ACTION,
        "entity_type": "task", "entity_id": task_id,
        "details": {
            "review_id": review_id, "reviewer_id": reviewer_id,
            "result": result, "criteria_total": len(normalized),
            "criteria_passed": passed, "evidence_ref": evidence_ref,
        },
    }
    try:
        validate_event(event)
    except AuditError as exc:
        raise QualityControlError(str(exc)) from exc
    return {
        "status": "review_candidate", "result": result,
        "criteria": normalized, "event": event,
        "persisted": False, "task_changed": False,
        "notification_sent": False, "read_only": True,
    }
