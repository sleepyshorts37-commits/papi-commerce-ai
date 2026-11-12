"""PAPI SALES ENGINE 1.48: read-only prospect pipeline and follow-up prioritization."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

STATUSES = {"new", "qualified", "contact_approved", "contacted", "interested",
            "quote_prepared", "won", "lost", "disqualified"}
FIELDS = {"prospect_id", "source", "sector", "need_summary", "status",
          "service_code", "owner", "next_follow_up_at", "created_at", "updated_at"}
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

def _normalize(raw: Any) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("Chaque prospect doit être un objet.")
    if set(raw) - FIELDS:
        raise ValueError("Champ inconnu ou donnée personnelle interdite dans ce registre.")
    required = {"prospect_id", "source", "sector", "need_summary", "status",
                "service_code", "owner", "created_at", "updated_at"}
    if not required.issubset(raw):
        raise ValueError("Champs obligatoires manquants.")
    status = raw["status"]
    if status not in STATUSES:
        raise ValueError("Statut de prospect inconnu.")
    created, updated = _date(raw["created_at"], "created_at"), _date(raw["updated_at"], "updated_at")
    if updated < created:
        raise ValueError("updated_at ne peut pas précéder created_at.")
    follow_up = _date(raw["next_follow_up_at"], "next_follow_up_at") if raw.get("next_follow_up_at") else None
    if status in {"won", "lost", "disqualified"} and follow_up:
        raise ValueError("Un prospect clôturé ne doit pas avoir de relance programmée.")
    return {
        "prospect_id": _text(raw["prospect_id"], "prospect_id"),
        "source": _text(raw["source"], "source"),
        "sector": _text(raw["sector"], "sector"),
        "need_summary": _text(raw["need_summary"], "need_summary", 500),
        "status": status,
        "service_code": _text(raw["service_code"], "service_code"),
        "owner": _text(raw["owner"], "owner"),
        "created_at": created.isoformat(),
        "updated_at": updated.isoformat(),
        "next_follow_up_at": follow_up.isoformat() if follow_up else None,
    }

def analyze_sales_pipeline(records: list[dict], *, as_of: str | None = None) -> dict:
    """Validate minimized CRM snapshots and return queues/metrics; performs no outreach."""
    if not isinstance(records, list):
        raise ValueError("records doit être une liste.")
    if len(records) > MAX_RECORDS:
        raise ValueError(f"Maximum de {MAX_RECORDS} prospects.")
    now = _date(as_of or datetime.now(timezone.utc).isoformat(), "as_of")
    valid, rejected, seen = [], [], set()
    for index, raw in enumerate(records):
        try:
            item = _normalize(raw)
            if item["prospect_id"] in seen:
                raise ValueError("prospect_id dupliqué.")
            seen.add(item["prospect_id"])
            valid.append(item)
        except (ValueError, TypeError, KeyError) as exc:
            rejected.append({"index": index, "reason": str(exc)})
    due, overdue, stale = [], [], []
    for item in valid:
        if item["status"] in {"won", "lost", "disqualified"}:
            continue
        follow_up = _date(item["next_follow_up_at"], "next_follow_up_at") if item["next_follow_up_at"] else None
        if follow_up and follow_up <= now:
            (overdue if follow_up < now else due).append(item["prospect_id"])
        age_days = (now - _date(item["updated_at"], "updated_at")).total_seconds() / 86400
        if age_days >= 7:
            stale.append(item["prospect_id"])
    counts = {status: sum(x["status"] == status for x in valid) for status in sorted(STATUSES)}
    active = sum(counts[s] for s in STATUSES - {"won", "lost", "disqualified"})
    closed = counts["won"] + counts["lost"]
    return {
        "as_of": now.isoformat(),
        "counts": {"valid": len(valid), "rejected": len(rejected), "active": active, "by_status": counts},
        "queues": {"overdue_follow_ups": overdue, "follow_ups_due": due, "stale_7_days_or_more": stale},
        "conversion": {"won": counts["won"], "lost": counts["lost"],
                       "closed_count": closed,
                       "win_rate_percent": round(counts["won"] * 100 / closed, 2) if closed else None},
        "records": valid,
        "rejected": rejected,
        "safety": {"read_only": True, "messages_sent": False, "external_contacts": False,
                   "automatic_reminders": False, "financial_actions": False,
                   "personal_contact_data_stored": False, "budget_xof": 0,
                   "human_approval_required": True,
                   "note": "contact_approved est un statut CRM, pas une autorisation technique d'envoyer un message."}
    }
