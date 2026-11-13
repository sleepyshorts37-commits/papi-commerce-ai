"""Conservative unit-economics evaluation for PAPI AI WORKERS offers.

All amounts are estimates in one explicitly declared currency. No FX conversion,
payment, purchase, contract acceptance or external action is performed.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from typing import Any

CURRENCY = re.compile(r"^[A-Z]{3}$")
CENT = Decimal("0.01")
PERCENT = Decimal("0.01")


class ProfitabilityError(ValueError):
    """Invalid offer economics input."""


def _amount(value: Any, field: str, *, allow_zero: bool = True) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ProfitabilityError(f"{field} doit être un montant numérique.")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ProfitabilityError(f"{field} doit être un montant numérique.") from None
    if not amount.is_finite() or amount < 0 or (not allow_zero and amount == 0):
        raise ProfitabilityError(f"{field} doit être fini et positif ou nul.")
    return amount


def _money(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def evaluate_offer_profitability(offer: dict[str, Any]) -> dict[str, Any]:
    """Estimate net profit after fees, operating costs and valued labor.

    Required amounts: gross_revenue, platform_fee, payout_fee,
    infrastructure_cost, other_cost, estimated_hours, labor_hourly_rate.
    """
    if not isinstance(offer, dict):
        raise ProfitabilityError("offer doit être un objet.")
    currency = offer.get("currency")
    if not isinstance(currency, str) or not CURRENCY.fullmatch(currency):
        raise ProfitabilityError("currency doit être un code ISO 4217 à trois lettres.")
    required = (
        "gross_revenue", "platform_fee", "payout_fee", "infrastructure_cost",
        "other_cost", "estimated_hours", "labor_hourly_rate",
    )
    values = {field: _amount(offer.get(field), field) for field in required}
    hours = values["estimated_hours"]
    if hours <= 0:
        raise ProfitabilityError("estimated_hours doit être strictement positif.")
    gross = values["gross_revenue"]
    fees = values["platform_fee"] + values["payout_fee"]
    operating = values["infrastructure_cost"] + values["other_cost"]
    labor = hours * values["labor_hourly_rate"]
    minimum_net_hourly = _amount(offer.get("minimum_net_hourly_rate", 0), "minimum_net_hourly_rate")
    cash_net = gross - fees - operating
    net_profit = cash_net - labor
    margin = (net_profit / gross * 100) if gross > 0 else Decimal("-100")
    hourly_net = net_profit / hours
    minimum_margin = _amount(offer.get("minimum_margin_percent", 0), "minimum_margin_percent")
    if minimum_margin > 100:
        raise ProfitabilityError("minimum_margin_percent ne peut pas dépasser 100.")

    if gross <= 0 or net_profit < 0:
        status = "loss_making"
    elif hourly_net < minimum_net_hourly:
        status = "below_hourly_target"
    elif margin < minimum_margin:
        status = "below_minimum_margin"
    else:
        status = "viable_for_human_review"

    return {
        "offer_id": str(offer.get("offer_id", "")).strip() or None,
        "currency": currency,
        "gross_revenue": _money(gross),
        "platform_and_payout_fees": _money(fees),
        "operating_costs": _money(operating),
        "estimated_labor_cost": _money(labor),
        "estimated_cash_net_before_labor": _money(cash_net),
        "estimated_net_profit_after_labor": _money(net_profit),
        "estimated_net_hourly_rate": _money(hourly_net),
        "estimated_net_margin_percent": _money(margin),
        "minimum_margin_percent": _money(minimum_margin),
        "minimum_net_hourly_rate": _money(minimum_net_hourly),
        "estimated_hours": str(hours),
        "status": status,
        "is_estimate": True,
        "currency_conversion_performed": False,
        "human_review_required": True,
        "spending_authorized": False,
        "contract_accepted": False,
        "external_actions_performed": False,
    }


def rank_offer_profitability(offers: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate and sort offers by net hourly return, then total net profit."""
    if not isinstance(offers, list):
        raise ProfitabilityError("offers doit être une liste.")
    results = [evaluate_offer_profitability(offer) for offer in offers]
    results.sort(
        key=lambda item: (
            Decimal(item["estimated_net_hourly_rate"]),
            Decimal(item["estimated_net_profit_after_labor"]),
        ),
        reverse=True,
    )
    for rank, item in enumerate(results, start=1):
        item["rank"] = rank
    return {
        "results": results,
        "offer_count": len(results),
        "viable_count": sum(item["status"] == "viable_for_human_review" for item in results),
        "loss_making_count": sum(item["status"] == "loss_making" for item in results),
        "ranking_method": "estimated_net_hourly_then_total_net_v1",
        "human_review_required": True,
        "external_actions_performed": False,
    }
