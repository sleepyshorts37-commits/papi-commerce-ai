"""Évaluation déterministe d'opportunités PAPI ; aucune action commerciale externe."""
from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Mapping

ACTIVITIES = {
    "PAPI MARKET", "PAPI DROPSHIPPING", "PAPI AFFILIATION",
    "PAPI FREELANCE", "PAPI SERVICES", "PAPI BUSINESS PARTNERS",
}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,79}$")
REQUIRED_FIELDS = {
    "id", "activity", "price_xof", "direct_cost_xof", "delivery_cost_xof",
    "commission_pct", "payment_fee_xof", "refund_reserve_pct",
    "initial_cost_xof", "customer_advance_xof", "supplier_payment_days",
    "customer_payment_days", "first_revenue_days", "risk_pct", "confidence_pct",
}
OPTIONAL_FIELDS = {"name"}
LOW_COST_THRESHOLD_XOF = 5_000
LOW_RISK_PCT = 25
FAST_CASH_IN_DAYS = 14


class OpportunityError(ValueError):
    """Données d'opportunité incomplètes ou incohérentes."""


def _money(data: Mapping[str, Any], field: str, *, minimum: int = 0) -> int:
    value = data.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise OpportunityError(f"{field} doit être un entier XOF supérieur ou égal à {minimum}.")
    return value


def _percentage(data: Mapping[str, Any], field: str) -> Decimal:
    value = data.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise OpportunityError(f"{field} doit être un pourcentage numérique entre 0 et 100.")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise OpportunityError(f"{field} est invalide.") from exc
    if not result.is_finite() or result < 0 or result > 100:
        raise OpportunityError(f"{field} doit être un pourcentage fini entre 0 et 100.")
    return result


def _percentage_amount(amount: int, percentage: Decimal) -> int:
    value = Decimal(amount) * percentage / Decimal(100)
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def evaluate_opportunity(item: Mapping[str, Any]) -> dict[str, Any]:
    """Calcule marge, besoin de trésorerie, rentabilité et priorité d'une option."""
    if not isinstance(item, Mapping):
        raise OpportunityError("Chaque opportunité doit être un objet.")
    missing = REQUIRED_FIELDS - set(item)
    unknown = set(item) - REQUIRED_FIELDS - OPTIONAL_FIELDS
    if missing:
        raise OpportunityError("Champs obligatoires manquants : " + ", ".join(sorted(missing)))
    if unknown:
        raise OpportunityError("Champs inconnus : " + ", ".join(sorted(unknown)))

    identifier = item["id"]
    if not isinstance(identifier, str) or not ID_RE.fullmatch(identifier):
        raise OpportunityError("id doit être un identifiant interne valide.")
    activity = item["activity"]
    if not isinstance(activity, str) or activity not in ACTIVITIES:
        raise OpportunityError("activity doit correspondre à l'une des six activités PAPI.")
    name = item.get("name", identifier)
    if not isinstance(name, str) or not name.strip() or len(name) > 120:
        raise OpportunityError("name doit être un texte non vide de 120 caractères maximum.")

    price = _money(item, "price_xof", minimum=1)
    direct_cost = _money(item, "direct_cost_xof")
    delivery_cost = _money(item, "delivery_cost_xof")
    payment_fee = _money(item, "payment_fee_xof")
    initial_cost = _money(item, "initial_cost_xof")
    customer_advance = _money(item, "customer_advance_xof")
    supplier_days = _money(item, "supplier_payment_days")
    customer_days = _money(item, "customer_payment_days")
    first_revenue_days = _money(item, "first_revenue_days")
    commission_pct = _percentage(item, "commission_pct")
    reserve_pct = _percentage(item, "refund_reserve_pct")
    risk_pct = _percentage(item, "risk_pct")
    confidence_pct = _percentage(item, "confidence_pct")
    if customer_advance > price:
        raise OpportunityError("customer_advance_xof ne peut dépasser price_xof.")

    commission = _percentage_amount(price, commission_pct)
    refund_reserve = _percentage_amount(price, reserve_pct)
    contribution = price - direct_cost - delivery_cost - payment_fee - commission - refund_reserve
    expected_contribution = _percentage_amount(contribution, confidence_pct)
    cash_in_days = first_revenue_days + customer_days

    supplier_outlay = direct_cost + delivery_cost + payment_fee
    if supplier_days <= customer_days:
        pre_receipt_gap = max(0, supplier_outlay - customer_advance)
    else:
        pre_receipt_gap = 0
    cash_required = initial_cost + pre_receipt_gap
    expected_net_after_setup = expected_contribution - initial_cost
    break_even_units = (
        math.ceil(initial_cost / expected_contribution)
        if expected_contribution > 0 and initial_cost > 0
        else (0 if initial_cost == 0 and expected_contribution > 0 else None)
    )
    roi_pct = (
        round((expected_net_after_setup / initial_cost) * 100, 2)
        if initial_cost > 0 else None
    )

    margin_score = max(0.0, min(100.0, (contribution / price) * 100))
    risk_score = 100.0 - float(risk_pct)
    speed_score = 100.0 / (1 + cash_in_days)
    liquidity_score = 100.0 / (1 + cash_required / 10_000)
    free_score = 100.0 if cash_required == 0 else 0.0
    ranking_score = round(
        0.25 * risk_score + 0.20 * speed_score + 0.15 * liquidity_score
        + 0.15 * free_score + 0.15 * margin_score + 0.10 * float(confidence_pct),
        2,
    )

    if cash_required == 0 and risk_pct <= LOW_RISK_PCT and cash_in_days <= FAST_CASH_IN_DAYS:
        priority_tier = 0
    elif cash_required == 0:
        priority_tier = 1
    elif cash_required <= LOW_COST_THRESHOLD_XOF and risk_pct <= 40 and cash_in_days <= 30:
        priority_tier = 2
    else:
        priority_tier = 3

    if contribution <= 0 or expected_net_after_setup < 0 or risk_pct >= 75:
        recommendation = "reject_or_rework"
        priority_tier = 4
    elif priority_tier == 0 and expected_net_after_setup > 0:
        recommendation = "owner_review_for_small_pilot"
    else:
        recommendation = "owner_review"

    return {
        "id": identifier, "name": name, "activity": activity, "currency": "XOF",
        "price_xof": price, "direct_cost_xof": direct_cost,
        "delivery_cost_xof": delivery_cost, "commission_xof": commission,
        "payment_fee_xof": payment_fee, "refund_reserve_xof": refund_reserve,
        "contribution_xof": contribution,
        "margin_pct": round((contribution / price) * 100, 2),
        "confidence_pct": float(confidence_pct),
        "expected_contribution_xof": expected_contribution,
        "initial_cost_xof": initial_cost, "cash_required_xof": cash_required,
        "cash_in_days": cash_in_days,
        "expected_net_after_setup_xof": expected_net_after_setup,
        "break_even_units": break_even_units, "roi_pct": roi_pct,
        "risk_pct": float(risk_pct), "priority_tier": priority_tier,
        "ranking_score": ranking_score, "recommendation": recommendation,
        "external_action_enabled": False,
    }


def rank_opportunities(items: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Classe d'abord les options sans besoin de trésorerie, peu risquées et rapides."""
    if not isinstance(items, list):
        raise OpportunityError("Les opportunités doivent être fournies sous forme de liste.")
    evaluated = [evaluate_opportunity(item) for item in items]
    identifiers = [item["id"] for item in evaluated]
    if len(identifiers) != len(set(identifiers)):
        raise OpportunityError("Les identifiants d'opportunité doivent être uniques.")
    evaluated.sort(
        key=lambda item: (
            item["priority_tier"], item["risk_pct"], item["cash_in_days"],
            -item["ranking_score"], -item["expected_net_after_setup_xof"], item["id"],
        )
    )
    for rank, item in enumerate(evaluated, start=1):
        item["rank"] = rank
    return evaluated
