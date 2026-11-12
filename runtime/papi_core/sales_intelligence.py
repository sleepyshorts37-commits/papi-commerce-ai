"""Sales-channel intelligence from aggregated, non-personal observations."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse


class SalesIntelligenceError(ValueError):
    """Sales observation is invalid."""


BUSINESS_LINES = {"PAPI MARKET", "PAPI DROPSHIPPING", "PAPI AFFILIATION",
                  "PAPI FREELANCE", "PAPI SERVICES", "PAPI BUSINESS PARTNERS"}
CHANNELS = {"whatsapp", "instagram", "facebook", "tiktok", "website",
            "email", "phone", "marketplace", "in_person", "referral", "other"}
SOURCE_TYPES = {"campaign_report", "platform_analytics", "crm_aggregate",
                "manual_count", "public_market_report"}


def _text(value: Any, field: str, limit: int = 250) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise SalesIntelligenceError(f"{field} doit être un texte non vide ({limit} caractères maximum).")
    value = value.strip()
    if "@" in value or any(token in value.lower() for token in ("password", "token=", "api_key")):
        raise SalesIntelligenceError(f"{field} contient une donnée sensible interdite.")
    return value


def _count(value: Any, field: str, *, required: bool = False) -> int | None:
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SalesIntelligenceError(f"{field} doit être un entier positif ou null.")
    return value


def _date(value: Any) -> datetime:
    if not isinstance(value, str):
        raise SalesIntelligenceError("observed_at doit être une date ISO 8601.")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SalesIntelligenceError("observed_at invalide.") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise SalesIntelligenceError("observed_at doit inclure un fuseau horaire.")
    return result.astimezone(timezone.utc)


def _source(value: Any) -> str:
    url = _text(value, "source_url", 1000)
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise SalesIntelligenceError("source_url doit être une URL HTTPS publique sans identifiants.")
    if parsed.hostname.lower() in {"localhost", "127.0.0.1", "::1"}:
        raise SalesIntelligenceError("Les URL locales sont interdites.")
    return url


def analyze_sales_channels(
    observations: list[dict[str, Any]], *, as_of: str, freshness_days: int = 30,
) -> dict[str, Any]:
    """Aggregate demand/channel evidence; no prospect identities or outreach."""
    if not isinstance(observations, list):
        raise SalesIntelligenceError("observations doit être une liste.")
    if isinstance(freshness_days, bool) or not isinstance(freshness_days, int) or not 1 <= freshness_days <= 365:
        raise SalesIntelligenceError("freshness_days doit être compris entre 1 et 365.")
    now = _date(as_of)
    analyzed, rejected, seen = [], [], set()
    for index, raw in enumerate(observations):
        try:
            if not isinstance(raw, dict):
                raise SalesIntelligenceError("L'observation doit être un objet.")
            required = {"business_line", "market", "customer_segment", "offer",
                        "channel", "source_type", "source_url", "observed_at",
                        "inquiries_count"}
            optional = {"qualified_count", "sales_count", "campaign_spend_xof",
                        "observation_window_days", "notes"}
            if not required.issubset(raw) or set(raw) - required - optional:
                raise SalesIntelligenceError("Champs manquants ou inconnus.")
            line = _text(raw["business_line"], "business_line")
            if line not in BUSINESS_LINES:
                raise SalesIntelligenceError("business_line non reconnue.")
            market = _text(raw["market"], "market")
            segment = _text(raw["customer_segment"], "customer_segment")
            offer = _text(raw["offer"], "offer")
            channel = _text(raw["channel"], "channel")
            if channel not in CHANNELS:
                raise SalesIntelligenceError("channel non reconnu.")
            source_type = _text(raw["source_type"], "source_type")
            if source_type not in SOURCE_TYPES:
                raise SalesIntelligenceError("source_type non reconnu.")
            source_url = _source(raw["source_url"])
            observed = _date(raw["observed_at"])
            if observed > now:
                raise SalesIntelligenceError("Observation datée dans le futur.")
            inquiries = _count(raw["inquiries_count"], "inquiries_count", required=True)
            qualified = _count(raw.get("qualified_count"), "qualified_count")
            sales = _count(raw.get("sales_count"), "sales_count")
            spend = _count(raw.get("campaign_spend_xof"), "campaign_spend_xof")
            window = raw.get("observation_window_days", 30)
            if isinstance(window, bool) or not isinstance(window, int) or not 1 <= window <= 365:
                raise SalesIntelligenceError("observation_window_days doit être compris entre 1 et 365.")
            if qualified is not None and qualified > inquiries:
                raise SalesIntelligenceError("qualified_count ne peut pas dépasser inquiries_count.")
            if sales is not None and qualified is not None and sales > qualified:
                raise SalesIntelligenceError("sales_count ne peut pas dépasser qualified_count.")
            if sales is not None and qualified is None and sales > inquiries:
                raise SalesIntelligenceError("sales_count ne peut pas dépasser inquiries_count.")
            notes = raw.get("notes", "")
            if not isinstance(notes, str) or len(notes) > 500 or "@" in notes:
                raise SalesIntelligenceError("notes invalide ou contenant une donnée personnelle.")
            key = (line, market.casefold(), segment.casefold(), offer.casefold(),
                   channel, source_url, observed.isoformat())
            if key in seen:
                continue
            seen.add(key)
            age = (now - observed).days
            conversion = round(qualified / inquiries * 100, 2) if qualified is not None and inquiries > 0 else None
            close_rate = round(sales / qualified * 100, 2) if sales is not None and qualified is not None and qualified > 0 else None
            cost_per_qualified = round(spend / qualified, 2) if spend is not None and qualified is not None and qualified > 0 else None
            analyzed.append({
                "business_line": line, "market": market, "customer_segment": segment,
                "offer": offer, "channel": channel, "source_type": source_type,
                "source_url": source_url,
                "observed_at": observed.isoformat().replace("+00:00", "Z"),
                "age_days": age, "fresh": age <= freshness_days,
                "observation_window_days": window,
                "inquiries_count": inquiries, "qualified_count": qualified,
                "sales_count": sales, "campaign_spend_xof": spend,
                "qualification_rate_percent": conversion,
                "qualified_to_sale_rate_percent": close_rate,
                "cost_per_qualified_lead_xof": cost_per_qualified,
                "evidence_status": "aggregate_source_reference_provided_not_fetched_or_verified",
            })
        except (SalesIntelligenceError, TypeError, KeyError) as exc:
            rejected.append({"index": index, "reason": str(exc)})
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in analyzed:
        groups.setdefault((row["business_line"], row["market"].casefold(),
                           row["customer_segment"].casefold()), []).append(row)
    comparisons = []
    for rows in groups.values():
        fresh_rows = [row for row in rows if row["fresh"]]
        # Rank only observed aggregate results; no inferred market share or future sales.
        ranked = sorted(fresh_rows, key=lambda row: (
            row["qualified_count"] is None,
            -(row["qualified_count"] or 0),
            row["cost_per_qualified_lead_xof"] is None,
            row["cost_per_qualified_lead_xof"] if row["cost_per_qualified_lead_xof"] is not None else float("inf"),
            row["channel"],
        ))
        comparisons.append({
            "business_line": rows[0]["business_line"],
            "market": rows[0]["market"],
            "customer_segment": rows[0]["customer_segment"],
            "fresh_channel_observations": len(fresh_rows),
            "observed_channels_ranked": [row["channel"] for row in ranked],
            "best_observed_channel": ranked[0]["channel"] if ranked and ranked[0]["qualified_count"] is not None else None,
            "ranking_basis": "fresh observed qualified leads, then observed cost per qualified lead; not a forecast",
            "no_evidence_message": None if ranked else "Aucune observation récente ; collecter des données avant de choisir un canal.",
        })
    analyzed.sort(key=lambda row: (not row["fresh"], row["business_line"],
                                   row["market"].casefold(), row["customer_segment"].casefold(),
                                   row["channel"]))
    return {
        "status": "available" if analyzed else "no_valid_sales_observations",
        "source": "user_supplied_aggregated_sales_observations",
        "observations_received": len(observations),
        "observations_analyzed": len(analyzed),
        "observations_rejected": len(rejected),
        "observations": analyzed,
        "channel_comparisons": comparisons,
        "limitations": [
            "Only aggregated, non-personal metrics are accepted; no prospect lists or contact details.",
            "Source URLs are not fetched or independently verified.",
            "Observed inquiries and sales are not total market demand or market share.",
            "Small or biased samples cannot establish channel performance or predict future revenue.",
        ],
        "controls": {"network_requests": 0, "prospects_contacted": 0,
                     "messages_sent": 0, "campaigns_launched": 0,
                     "spending_xof": 0, "sales_actions_executed": 0, "read_only": True},
    }
