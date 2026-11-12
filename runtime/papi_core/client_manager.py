"""PAPI CLIENT MANAGER 1.50: privacy-minimized service and satisfaction records."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

REQUEST_STATUSES = {"open", "in_progress", "waiting", "resolved", "closed", "cancelled"}
FEEDBACK_STATUSES = {"received", "reviewed", "action_planned", "resolved", "closed"}
ALLOWED_REQUEST_FIELDS = {"case_id", "client_ref", "service_code", "category", "summary",
                          "status", "created_at", "updated_at", "resolved_at"}
ALLOWED_FEEDBACK_FIELDS = {"feedback_id", "client_ref", "case_id", "rating",
                           "comment", "status", "created_at", "updated_at"}
ALLOWED_SERVICE_FIELDS = {"service_code", "delivery_count", "satisfaction_total",
                          "satisfaction_count", "complaint_count"}
MAX_RECORDS = 500

def _date(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} doit être une date ISO 8601.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} doit être une date ISO 8601.") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)

def _text(value: Any, field: str, limit: int = 120) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ValueError(f"{field} invalide.")
    return value.strip()

def _fields(raw: Any, allowed: set[str], required: set[str], label: str) -> dict:
    if not isinstance(raw, dict):
        raise ValueError(f"Chaque {label} doit être un objet.")
    if set(raw) - allowed:
        raise ValueError("Champ inconnu ou donnée personnelle interdite.")
    if not required.issubset(raw):
        raise ValueError(f"Champs obligatoires manquants dans {label}.")
    return raw

def _request(raw: Any) -> dict:
    x = _fields(raw, ALLOWED_REQUEST_FIELDS,
                {"case_id", "client_ref", "service_code", "category", "summary",
                 "status", "created_at", "updated_at"}, "dossier")
    status = x["status"]
    if status not in REQUEST_STATUSES:
        raise ValueError("Statut de dossier inconnu.")
    created, updated = _date(x["created_at"], "created_at"), _date(x["updated_at"], "updated_at")
    if updated < created:
        raise ValueError("updated_at ne peut pas précéder created_at.")
    resolved = _date(x["resolved_at"], "resolved_at") if x.get("resolved_at") else None
    if resolved and not created <= resolved <= updated:
        raise ValueError("resolved_at doit être compris entre created_at et updated_at.")
    if status in {"resolved", "closed"} and resolved is None:
        raise ValueError("Un dossier résolu ou clôturé doit avoir resolved_at.")
    return {"case_id": _text(x["case_id"], "case_id"),
            "client_ref": _text(x["client_ref"], "client_ref"),
            "service_code": _text(x["service_code"], "service_code"),
            "category": _text(x["category"], "category"),
            "summary": _text(x["summary"], "summary", 500),
            "status": status, "created_at": created.isoformat(),
            "updated_at": updated.isoformat(),
            "resolved_at": resolved.isoformat() if resolved else None}

def _feedback(raw: Any, case_ids: set[str]) -> dict:
    x = _fields(raw, ALLOWED_FEEDBACK_FIELDS,
                {"feedback_id", "client_ref", "rating", "status", "created_at", "updated_at"},
                "avis")
    case_id = x.get("case_id")
    if case_id is not None and case_id not in case_ids:
        raise ValueError("L'avis référence un dossier inconnu.")
    rating = x["rating"]
    if rating is not None and (isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5):
        raise ValueError("rating doit être compris entre 1 et 5.")
    status = x["status"]
    if status not in FEEDBACK_STATUSES:
        raise ValueError("Statut d'avis inconnu.")
    created, updated = _date(x["created_at"], "created_at"), _date(x["updated_at"], "updated_at")
    if updated < created:
        raise ValueError("updated_at ne peut pas précéder created_at.")
    comment = x.get("comment")
    if comment is not None and (not isinstance(comment, str) or len(comment) > 500):
        raise ValueError("comment invalide.")
    return {"feedback_id": _text(x["feedback_id"], "feedback_id"),
            "client_ref": _text(x["client_ref"], "client_ref"),
            "case_id": case_id, "rating": rating, "comment": comment,
            "status": status, "created_at": created.isoformat(), "updated_at": updated.isoformat()}

def _service(raw: Any) -> dict:
    x = _fields(raw, ALLOWED_SERVICE_FIELDS,
                {"service_code", "delivery_count", "satisfaction_total",
                 "satisfaction_count", "complaint_count"}, "indicateur de service")
    counts = {}
    for key in ("delivery_count", "satisfaction_total", "satisfaction_count", "complaint_count"):
        value = x[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{key} doit être un entier positif ou nul.")
        counts[key] = value
    if counts["satisfaction_total"] > 5 * counts["satisfaction_count"]:
        raise ValueError("satisfaction_total dépasse le maximum possible.")
    if counts["satisfaction_count"] > counts["delivery_count"]:
        raise ValueError("Le nombre d'avis ne peut pas dépasser les prestations livrées.")
    average = round(counts["satisfaction_total"] / counts["satisfaction_count"], 2) if counts["satisfaction_count"] else None
    return {"service_code": _text(x["service_code"], "service_code"), **counts,
            "average_rating": average,
            "complaint_rate_percent": round(counts["complaint_count"] * 100 / counts["delivery_count"], 2) if counts["delivery_count"] else None}

def analyze_client_experience(cases: list[dict], feedback: list[dict],
                              service_metrics: list[dict] | None = None,
                              *, as_of: str | None = None) -> dict:
    """Analyze minimized client-service snapshots; no messaging or client contact."""
    if not isinstance(cases, list) or not isinstance(feedback, list):
        raise ValueError("cases et feedback doivent être des listes.")
    if service_metrics is None:
        service_metrics = []
    if not isinstance(service_metrics, list):
        raise ValueError("service_metrics doit être une liste.")
    if any(len(group) > MAX_RECORDS for group in (cases, feedback, service_metrics)):
        raise ValueError(f"Maximum de {MAX_RECORDS} enregistrements par catégorie.")
    now = _date(as_of or datetime.now(timezone.utc).isoformat(), "as_of")
    valid_cases, valid_feedback, valid_services = [], [], []
    rejected = []
    for label, records, target, validator in (
        ("case", cases, valid_cases, _request),
    ):
        seen = set()
        for index, raw in enumerate(records):
            try:
                item = validator(raw)
                if item["case_id"] in seen:
                    raise ValueError("case_id dupliqué.")
                seen.add(item["case_id"])
                if _date(item["created_at"], "created_at") > now:
                    raise ValueError("created_at est dans le futur.")
                target.append(item)
            except (ValueError, TypeError, KeyError) as exc:
                rejected.append({"category": label, "index": index, "reason": str(exc)})
    case_ids = {x["case_id"] for x in valid_cases}
    for index, raw in enumerate(feedback):
        try:
            item = _feedback(raw, case_ids)
            if _date(item["created_at"], "created_at") > now:
                raise ValueError("created_at est dans le futur.")
            if any(x["feedback_id"] == item["feedback_id"] for x in valid_feedback):
                raise ValueError("feedback_id dupliqué.")
            valid_feedback.append(item)
        except (ValueError, TypeError, KeyError) as exc:
            rejected.append({"category": "feedback", "index": index, "reason": str(exc)})
    for index, raw in enumerate(service_metrics):
        try:
            item = _service(raw)
            if any(x["service_code"] == item["service_code"] for x in valid_services):
                raise ValueError("service_code dupliqué.")
            valid_services.append(item)
        except (ValueError, TypeError, KeyError) as exc:
            rejected.append({"category": "service_metric", "index": index, "reason": str(exc)})
    by_status = {status: sum(x["status"] == status for x in valid_cases) for status in sorted(REQUEST_STATUSES)}
    ratings = [x["rating"] for x in valid_feedback if x["rating"] is not None]
    unresolved_feedback = [x["feedback_id"] for x in valid_feedback if x["status"] not in {"resolved", "closed"}]
    open_cases = [x["case_id"] for x in valid_cases if x["status"] not in {"resolved", "closed", "cancelled"}]
    return {
        "as_of": now.isoformat(),
        "cases": {"valid": len(valid_cases), "by_status": by_status, "open_case_ids": open_cases},
        "feedback": {"valid": len(valid_feedback), "rated_count": len(ratings),
                     "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
                     "unresolved_feedback_ids": unresolved_feedback},
        "service_metrics": valid_services,
        "rejected": rejected,
        "safety": {"read_only": True, "client_contact": False, "messages_sent": False,
                   "automatic_follow_ups": False, "personal_contact_data_stored": False,
                   "budget_xof": 0, "human_review_required": True,
                   "note": "Utiliser des références client internes pseudonymisées. Les commentaires libres doivent être expurgés de toute donnée personnelle ou sensible avant import."}
    }
