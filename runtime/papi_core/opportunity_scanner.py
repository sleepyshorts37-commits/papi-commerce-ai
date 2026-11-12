"""Collecteur et classement de signaux commerciaux fournis explicitement, sans scraping."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from .business_intelligence import BUSINESS_LINES, BusinessIntelligenceError

TEXT_FIELDS = ("source", "source_ref", "observed_at", "business_line",
               "market", "customer_segment", "offer")
OPTIONAL_FIELDS = ("problem_observed", "proposed_solution", "contact_channel",
                   "expected_price_xof", "variable_cost_xof", "acquisition_cost_xof",
                   "fulfillment_cost_xof", "estimated_monthly_volume",
                   "time_to_first_revenue_days", "upfront_cost_xof")
SENSITIVE_MARKERS = ("password", "token", "secret", "phone", "email", "address",
                     "customer_name", "personal_data")


class OpportunityScannerError(ValueError):
    """Signal commercial invalide ou dangereux."""


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise OpportunityScannerError("observed_at doit être une date ISO 8601.")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OpportunityScannerError("observed_at invalide.") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise OpportunityScannerError("observed_at doit inclure un fuseau horaire.")
    return result.astimezone(timezone.utc)


def _safe_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 500:
        raise OpportunityScannerError(f"{field} doit être un texte non vide de 500 caractères maximum.")
    normalized = value.strip()
    lowered = normalized.lower()
    if any(marker in lowered for marker in SENSITIVE_MARKERS):
        raise OpportunityScannerError(f"{field} contient un marqueur de donnée sensible interdit.")
    return normalized


def _fingerprint(signal: dict[str, Any]) -> str:
    identity = {key: signal[key].casefold() for key in
                ("source", "source_ref", "business_line", "market", "offer")}
    payload = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def scan_opportunity_signals(
    signals: list[dict[str, Any]], *, as_of: str,
    freshness_days: int = 30,
) -> dict[str, Any]:
    """Classe les signaux reçus en entrée ; n'effectue aucune recherche réseau."""
    if not isinstance(signals, list):
        raise OpportunityScannerError("signals doit être une liste.")
    if isinstance(freshness_days, bool) or not isinstance(freshness_days, int) or not 1 <= freshness_days <= 365:
        raise OpportunityScannerError("freshness_days doit être compris entre 1 et 365.")
    cutoff = _timestamp(as_of)
    window = timedelta(days=freshness_days)
    seen, accepted, rejected, duplicates = set(), [], [], 0

    for index, raw in enumerate(signals):
        try:
            if not isinstance(raw, dict):
                raise OpportunityScannerError("Le signal doit être un objet.")
            required = set(TEXT_FIELDS)
            if not required.issubset(raw) or set(raw) - set(TEXT_FIELDS) - set(OPTIONAL_FIELDS):
                raise OpportunityScannerError("Champs manquants ou inconnus dans le signal.")
            item = {key: _safe_text(raw[key], key) for key in TEXT_FIELDS if key != "observed_at"}
            moment = _timestamp(raw["observed_at"])
            if item["business_line"] not in BUSINESS_LINES:
                raise OpportunityScannerError("business_line non reconnu.")
            if moment > cutoff:
                raise OpportunityScannerError("Signal daté dans le futur.")
            optional = {}
            for key in OPTIONAL_FIELDS:
                value = raw.get(key)
                if value is not None:
                    if key.endswith("_xof") or key in {"estimated_monthly_volume", "time_to_first_revenue_days"}:
                        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                            raise OpportunityScannerError(f"{key} doit être un entier positif ou null.")
                    else:
                        value = _safe_text(value, key)
                    optional[key] = value
            normalized = {**item, "observed_at": moment.isoformat().replace("+00:00", "Z"), **optional}
            fingerprint = _fingerprint(normalized)
            if fingerprint in seen:
                duplicates += 1
                continue
            seen.add(fingerprint)
            age = cutoff - moment
            missing = [key for key in ("problem_observed", "proposed_solution",
                       "expected_price_xof", "estimated_monthly_volume") if key not in optional]
            completeness = 100 - (25 * len(missing))
            freshness = max(0, 100 - int(age.total_seconds() / window.total_seconds() * 100))
            score = round(completeness * 0.7 + freshness * 0.3)
            status = "stale" if age > window else "needs_enrichment" if missing else "ready_for_business_analysis"
            accepted.append({
                "signal_id": fingerprint[:20], "fingerprint": fingerprint,
                **normalized, "age_days": age.days, "freshness_score": freshness,
                "completeness_score": completeness, "triage_score": score,
                "missing_fields": missing, "triage_status": status,
                "evidence_status": "source_reference_provided_not_verified",
            })
        except (OpportunityScannerError, BusinessIntelligenceError, TypeError, KeyError) as exc:
            rejected.append({"index": index, "reason": str(exc)})

    accepted.sort(key=lambda x: (x["triage_status"] != "ready_for_business_analysis",
                                 x["triage_status"] == "stale", -x["triage_score"], x["signal_id"]))
    return {
        "status": "available" if accepted else "no_valid_signals",
        "source": "explicitly_supplied_signal_records",
        "signals_received": len(signals), "signals_accepted": len(accepted),
        "duplicates_skipped": duplicates, "signals_rejected": len(rejected),
        "signals": accepted, "rejections": rejected,
        "controls": {
            "network_requests": 0, "web_scraping_performed": False,
            "external_research_performed": False, "messages_sent": 0,
            "customer_data_collected": False, "spending_xof": 0,
            "actions_executed": 0, "read_only": True,
        },
    }
