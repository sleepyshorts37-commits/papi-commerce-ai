"""Unified, read-only operational report for PAPI AI WORKERS.

Consumes already-reviewed records. It does not discover platforms, send alerts,
resume workflows, accept contracts, or perform financial/external actions.
"""
from __future__ import annotations

from typing import Any


class WorkersReportError(ValueError):
    """Invalid report input."""


def _records(value: Any, field: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise WorkersReportError(f"{field} doit être une liste d'objets.")
    return value


def build_workers_report(
    *,
    platform_candidates: list[dict[str, Any]] | None = None,
    handoffs: list[dict[str, Any]] | None = None,
    profitability_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Summarize discovery, human intervention queue and economics results."""
    platforms = _records(platform_candidates, "platform_candidates")
    pending = _records(handoffs, "handoffs")
    economics = _records(profitability_results, "profitability_results")

    platform_counts = {
        state: sum(item.get("status") == state for item in platforms)
        for state in (
            "candidate", "needs_human_review", "human_registration_required",
            "rejected", "verified_ready", "suspended",
        )
    }
    handoff_counts = {
        state: sum(item.get("status") == state for item in pending)
        for state in (
            "awaiting_user", "user_confirmed", "resumed", "completed", "rejected",
        )
    }
    profitability_counts = {
        state: sum(item.get("status") == state for item in economics)
        for state in (
            "viable_for_human_review", "below_minimum_margin",
            "below_hourly_target", "loss_making",
        )
    }

    user_actions = [
        {
            "handoff_id": item.get("handoff_id"),
            "platform_name": item.get("platform_name"),
            "official_url": item.get("official_url"),
            "required_user_action": item.get("required_user_action"),
            "status": item.get("status"),
        }
        for item in pending if item.get("status") == "awaiting_user"
    ]
    review_platforms = [
        {
            "platform_id": item.get("platform_id"),
            "name": item.get("name"),
            "url": item.get("url"),
            "status": item.get("status"),
            "blockers": list(item.get("blockers", []))
                if isinstance(item.get("blockers", []), list) else [],
        }
        for item in platforms
        if item.get("status") in {"needs_human_review", "human_registration_required"}
    ]
    viable_offers = [
        {
            "offer_id": item.get("offer_id"),
            "currency": item.get("currency"),
            "estimated_net_profit_after_labor": item.get("estimated_net_profit_after_labor"),
            "estimated_net_hourly_rate": item.get("estimated_net_hourly_rate"),
            "estimated_net_margin_percent": item.get("estimated_net_margin_percent"),
            "status": item.get("status"),
        }
        for item in economics if item.get("status") == "viable_for_human_review"
    ]

    return {
        "report_type": "papi_ai_workers_unified_status_v1",
        "platforms": {
            "total": len(platforms),
            "by_status": platform_counts,
            "requiring_review": review_platforms,
        },
        "human_handoffs": {
            "total": len(pending),
            "by_status": handoff_counts,
            "awaiting_user_count": len(user_actions),
            "user_actions": user_actions,
        },
        "profitability": {
            "total": len(economics),
            "by_status": profitability_counts,
            "offers_for_human_review": viable_offers,
            "currency_conversion_performed": False,
        },
        "governance": {
            "human_review_required": True,
            "spending_authorized": False,
            "contracts_accepted": False,
            "external_actions_performed": False,
            "live_search_performed": False,
            "notifications_sent": False,
            "source_records_verified_by_report": False,
        },
        "limitations": [
            "Rapport calculé uniquement à partir des enregistrements fournis.",
            "Les états et estimations ne constituent pas une vérification indépendante.",
            "Aucune recherche, notification, inscription, dépense ou action externe n'est exécutée.",
        ],
    }
