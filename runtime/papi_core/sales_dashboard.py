"""PAPI SALES DASHBOARD 1.49: read-only consolidated commercial overview."""
from __future__ import annotations
from typing import Any

def _mapping(value: Any, field: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{field} doit être un objet.")
    return value

def _nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} doit être un entier positif ou nul.")
    return value

def build_sales_dashboard(sales_pipeline: dict, services_overview: dict | None = None) -> dict:
    """Combine already-computed local snapshots; never fetches or changes source data."""
    sales = _mapping(sales_pipeline, "sales_pipeline")
    counts = _mapping(sales.get("counts"), "counts")
    by_status = _mapping(counts.get("by_status"), "counts.by_status")
    queues = _mapping(sales.get("queues"), "queues")
    conversion = _mapping(sales.get("conversion"), "conversion")
    total = _nonnegative_int(counts.get("valid"), "counts.valid")
    rejected = _nonnegative_int(counts.get("rejected"), "counts.rejected")
    statuses = {str(k): _nonnegative_int(v, f"by_status.{k}") for k, v in by_status.items()}
    for key in ("overdue_follow_ups", "follow_ups_due", "stale_7_days_or_more"):
        if not isinstance(queues.get(key), list):
            raise ValueError(f"queues.{key} doit être une liste.")
    won = _nonnegative_int(conversion.get("won"), "conversion.won")
    lost = _nonnegative_int(conversion.get("lost"), "conversion.lost")
    closed = _nonnegative_int(conversion.get("closed_count"), "conversion.closed_count")
    if won + lost != closed:
        raise ValueError("Les conversions clôturées doivent correspondre aux ventes gagnées et perdues.")
    win_rate = conversion.get("win_rate_percent")
    if win_rate is not None and (isinstance(win_rate, bool) or not isinstance(win_rate, (int, float)) or not 0 <= win_rate <= 100):
        raise ValueError("win_rate_percent invalide.")
    service_cards = None
    if services_overview is not None:
        services = _mapping(services_overview, "services_overview")
        service_counts = _mapping(services.get("counts"), "services.counts")
        funnel = _mapping(services.get("funnel"), "services.funnel")
        revenue = _mapping(services.get("revenue"), "services.revenue")
        service_cards = {
            "requests": _nonnegative_int(service_counts.get("requests"), "services.requests"),
            "quotes": _nonnegative_int(service_counts.get("quotes"), "services.quotes"),
            "work_items": _nonnegative_int(service_counts.get("work_items"), "services.work_items"),
            "rejected_records": _nonnegative_int(service_counts.get("rejected_records"), "services.rejected_records"),
            "new_requests": _nonnegative_int(funnel.get("new_requests"), "services.new_requests"),
            "quotes_accepted": _nonnegative_int(funnel.get("quotes_accepted"), "services.quotes_accepted"),
            "work_in_progress": _nonnegative_int(funnel.get("work_in_progress"), "services.work_in_progress"),
            "work_delivered": _nonnegative_int(funnel.get("work_delivered"), "services.work_delivered"),
            "recognized_revenue_xof": _nonnegative_int(revenue.get("recognized_xof"), "services.recognized_xof"),
            "verified_payment_count": _nonnegative_int(revenue.get("verified_payment_count"), "services.verified_payment_count"),
            "revenue_note": revenue.get("note", "Vérifier chaque paiement auprès du prestataire.")
        }
    priorities = []
    if queues["overdue_follow_ups"]:
        priorities.append({"priority": "high", "category": "overdue_follow_up", "count": len(queues["overdue_follow_ups"])})
    if queues["follow_ups_due"]:
        priorities.append({"priority": "normal", "category": "follow_up_due", "count": len(queues["follow_ups_due"])})
    if queues["stale_7_days_or_more"]:
        priorities.append({"priority": "normal", "category": "stale_prospect", "count": len(queues["stale_7_days_or_more"])})
    return {
        "as_of": sales.get("as_of"),
        "sales": {"valid_prospects": total, "rejected_records": rejected,
                  "by_status": statuses, "won": won, "lost": lost,
                  "closed_count": closed, "win_rate_percent": win_rate},
        "follow_ups": {"overdue_count": len(queues["overdue_follow_ups"]),
                       "due_count": len(queues["follow_ups_due"]),
                       "stale_count": len(queues["stale_7_days_or_more"]),
                       "overdue_ids": list(queues["overdue_follow_ups"]),
                       "due_ids": list(queues["follow_ups_due"]),
                       "stale_ids": list(queues["stale_7_days_or_more"])},
        "service_operations": service_cards,
        "priorities": priorities,
        "safety": {"read_only": True, "source_snapshots_modified": False,
                   "external_contacts": False, "messages_sent": False,
                   "automatic_reminders": False, "financial_actions": False,
                   "budget_xof": 0,
                   "note": "Les statuts CRM ne prouvent pas un encaissement. Le chiffre d'affaires doit être confirmé indépendamment auprès du prestataire de paiement."}
    }
