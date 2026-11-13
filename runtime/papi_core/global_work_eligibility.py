"""Conservative country, policy and unit-economics qualification for work leads."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
from typing import Any

class GlobalWorkEligibilityError(ValueError):
    """Invalid eligibility or economic input."""

def _money(value: Any, field: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise GlobalWorkEligibilityError(f"{field} doit être un montant numérique.")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise GlobalWorkEligibilityError(f"{field} invalide.") from exc
    if not amount.is_finite() or amount < 0:
        raise GlobalWorkEligibilityError(f"{field} doit être positif ou nul.")
    return amount

def evaluate_work_opportunity(candidate: dict[str, Any], *, applicant_country: str = "SN") -> dict[str, Any]:
    """Evaluate supplied evidence only; never browse, apply, register or pay."""
    if not isinstance(candidate, dict):
        raise GlobalWorkEligibilityError("Un candidat structuré est requis.")
    if not isinstance(applicant_country, str) or not applicant_country.strip():
        raise GlobalWorkEligibilityError("Le pays du candidat est requis.")
    gaps, blockers = [], []
    evidence = candidate.get("evidence", {})
    if not isinstance(evidence, dict):
        raise GlobalWorkEligibilityError("evidence doit être un objet.")
    countries = candidate.get("eligible_countries")
    if not isinstance(countries, list) or not countries:
        gaps.append("eligible_countries")
        country_status = "unknown"
    elif applicant_country.upper() in [str(x).upper() for x in countries]:
        country_status = "listed"
    else:
        country_status = "not_listed"
        blockers.append("applicant_country_not_listed")
    payout = candidate.get("payout")
    if not isinstance(payout, dict):
        payout = {}
    amount_raw, currency = payout.get("amount"), payout.get("currency")
    gross = _money(amount_raw, "payout.amount") if amount_raw is not None else None
    if gross is None: gaps.append("payout.amount")
    if not isinstance(currency, str) or not currency.strip(): gaps.append("payout.currency")
    methods = payout.get("methods")
    if not isinstance(methods, list) or not any(str(x).strip() for x in methods):
        gaps.append("payout.methods")
    fees = _money(candidate["fees"], "fees") if candidate.get("fees") is not None else None
    upfront = _money(candidate["upfront_cost"], "upfront_cost") if candidate.get("upfront_cost") is not None else None
    if fees is None: gaps.append("fees")
    if upfront is None: gaps.append("upfront_cost")
    hours = _money(candidate["estimated_hours"], "estimated_hours") if candidate.get("estimated_hours") is not None else None
    if hours is None: gaps.append("estimated_hours")
    elif hours == 0: blockers.append("estimated_hours_must_be_positive")
    if not isinstance(candidate.get("kyc_required"), bool): gaps.append("kyc_required")
    ai_policy = candidate.get("ai_policy")
    if ai_policy not in {"allowed", "restricted", "prohibited", "unknown"}: gaps.append("ai_policy")
    elif ai_policy == "prohibited": blockers.append("ai_use_prohibited")
    presence = candidate.get("human_presence")
    if presence not in {"not_required", "required"}: gaps.append("human_presence")
    for key in ("country_eligibility", "payout_terms", "fees", "kyc", "ai_policy"):
        if not isinstance(evidence.get(key), str) or not evidence[key].strip():
            gaps.append("evidence." + key)
    net = hourly = None
    if gross is not None and fees is not None and upfront is not None:
        net = gross - fees - upfront
        if net < 0: blockers.append("negative_net_payout")
        if hours is not None and hours > 0: hourly = net / hours
    gaps, blockers = sorted(set(gaps)), sorted(set(blockers))
    status = "rejected_or_manual_review" if blockers else ("insufficient_evidence" if gaps else "ready_for_human_review")
    return {
        "status": status, "applicant_country": applicant_country.upper(),
        "country_status": country_status, "missing_fields": gaps, "blockers": blockers,
        "gross_payout": str(gross) if gross is not None else None,
        "fees": str(fees) if fees is not None else None,
        "upfront_cost": str(upfront) if upfront is not None else None,
        "estimated_net": str(net) if net is not None else None,
        "estimated_hourly_net": str(hourly) if hourly is not None else None,
        "currency": currency.strip().upper() if isinstance(currency, str) and currency.strip() else None,
        "qualified": False, "human_approval_required": True,
        "application_submitted": False, "payment_made": False,
    }
