"""Read-only revenue and contribution planning from explicit offer observations."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

BUSINESS_LINES = {"PAPI MARKET", "PAPI DROPSHIPPING", "PAPI AFFILIATION",
                  "PAPI FREELANCE", "PAPI SERVICES", "PAPI BUSINESS PARTNERS"}


class RevenueOptimizationError(ValueError):
    """Invalid revenue-planning input."""


def _integer(value: Any, field: str, *, optional: bool = False) -> int | None:
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RevenueOptimizationError(f"{field} doit être un entier positif ou nul.")
    return value


def _label(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 200:
        raise RevenueOptimizationError(f"{field} doit être un texte non vide (200 caractères maximum).")
    value = value.strip()
    if "@" in value or any(x in value.lower() for x in ("password", "token=", "api_key")):
        raise RevenueOptimizationError(f"{field} contient une donnée sensible interdite.")
    return value


def _date(value: Any) -> datetime:
    if not isinstance(value, str):
        raise RevenueOptimizationError("observed_at doit être une date ISO 8601 avec fuseau.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RevenueOptimizationError("observed_at invalide.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RevenueOptimizationError("observed_at doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)


def optimize_revenue(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate unit economics and explicitly hypothetical targets; never executes."""
    if not isinstance(observations, list):
        raise RevenueOptimizationError("observations doit être une liste.")
    results, rejected, seen = [], [], set()
    required = {"offer_name", "business_line", "market", "currency",
                "selling_price_xof", "unit_variable_cost_xof"}
    optional = {"fixed_cost_xof", "fixed_cost_period", "sales_count",
                "target_sales_count", "commission_rate_bps", "commission_fixed_xof",
                "payment_verification_status", "verified_paid_units",
                "verified_paid_revenue_xof", "source_ref", "observed_at",
                "alternative_prices_xof"}
    for index, raw in enumerate(observations):
        try:
            if not isinstance(raw, dict) or not required.issubset(raw) or set(raw) - required - optional:
                raise RevenueOptimizationError("Champs obligatoires manquants ou champs inconnus.")
            name = _label(raw["offer_name"], "offer_name")
            line = _label(raw["business_line"], "business_line")
            if line not in BUSINESS_LINES:
                raise RevenueOptimizationError("business_line non reconnue.")
            market = _label(raw["market"], "market")
            if raw["currency"] != "XOF":
                raise RevenueOptimizationError("Seule la devise XOF est acceptée.")
            price = _integer(raw["selling_price_xof"], "selling_price_xof")
            variable = _integer(raw["unit_variable_cost_xof"], "unit_variable_cost_xof")
            fixed = _integer(raw.get("fixed_cost_xof"), "fixed_cost_xof", optional=True)
            fixed_period = raw.get("fixed_cost_period")
            if fixed is not None:
                fixed_period = _label(fixed_period, "fixed_cost_period")
            elif fixed_period is not None:
                raise RevenueOptimizationError("fixed_cost_period nécessite fixed_cost_xof.")
            sales = _integer(raw.get("sales_count"), "sales_count", optional=True)
            target = _integer(raw.get("target_sales_count"), "target_sales_count", optional=True)
            rate = _integer(raw.get("commission_rate_bps", 0), "commission_rate_bps")
            commission_fixed = _integer(raw.get("commission_fixed_xof", 0), "commission_fixed_xof")
            if rate > 10000:
                raise RevenueOptimizationError("commission_rate_bps ne peut dépasser 10000.")
            payment_status = raw.get("payment_verification_status", "unverified")
            paid_units = raw.get("verified_paid_units")
            paid_revenue = raw.get("verified_paid_revenue_xof")
            if payment_status == "verified":
                paid_units = _integer(paid_units, "verified_paid_units")
                paid_revenue = _integer(paid_revenue, "verified_paid_revenue_xof")
                if paid_units is None or paid_revenue is None:
                    raise RevenueOptimizationError("Les unités et recettes payées vérifiées sont obligatoires.")
            else:
                if payment_status != "unverified" or paid_units is not None or paid_revenue is not None:
                    raise RevenueOptimizationError("Les recettes payées ne peuvent être déclarées sans statut verified.")
                paid_units = paid_revenue = None
            source_ref = raw.get("source_ref")
            if source_ref is not None:
                source_ref = _label(source_ref, "source_ref")
            observed_at = raw.get("observed_at")
            if observed_at is not None:
                observed_at = _date(observed_at).isoformat().replace("+00:00", "Z")
            alternatives = raw.get("alternative_prices_xof", [])
            if not isinstance(alternatives, list):
                raise RevenueOptimizationError("alternative_prices_xof doit être une liste.")
            alternatives = [_integer(x, "alternative_prices_xof") for x in alternatives]
            key = (line, market.casefold(), name.casefold(), price, variable, source_ref, observed_at)
            if key in seen:
                continue
            seen.add(key)
            contribution = price - variable
            commission_per_unit = (price * rate + 9999) // 10000 + commission_fixed
            net_unit = contribution - commission_per_unit
            break_even = ((fixed + contribution - 1) // contribution
                          if fixed is not None and contribution > 0 else None)
            target_gross = price * target if target is not None else None
            target_contribution = ((net_unit * target - fixed) if target is not None and fixed is not None
                                   else net_unit * target if target is not None else None)
            results.append({
                "offer_name": name, "business_line": line, "market": market, "currency": "XOF",
                "selling_price_xof": price, "unit_variable_cost_xof": variable,
                "unit_contribution_xof": contribution,
                "contribution_margin_percent": round(contribution / price * 100, 2) if price > 0 else None,
                "commission_rate_bps": rate, "commission_fixed_xof": commission_fixed,
                "commission_per_unit_xof": commission_per_unit,
                "net_contribution_after_commission_xof": net_unit,
                "fixed_cost_xof": fixed, "fixed_cost_period": fixed_period,
                "break_even_units": break_even,
                "break_even_status": ("calculable" if break_even is not None else
                                      "unknown_missing_fixed_cost" if fixed is None else "not_reachable_nonpositive_contribution"),
                "observed_sales_count": sales,
                "target_sales_count": target,
                "target_gross_revenue_xof": target_gross,
                "target_contribution_after_commission_xof": target_contribution,
                "target_status": "hypothetical_planning_not_forecast" if target is not None else "no_target_supplied",
                "verified_paid_units": paid_units,
                "verified_paid_revenue_xof": paid_revenue,
                "realized_revenue_status": "verified_reconciled_payment_data" if payment_status == "verified" else "unknown_unverified",
                "realized_revenue_xof": paid_revenue if payment_status == "verified" else None,
                "realized_commission_xof": (commission_per_unit * paid_units if payment_status == "verified" else None),
                "price_warning": "selling_price_below_variable_cost" if contribution < 0 else None,
                "price_scenarios": [{
                    "selling_price_xof": p,
                    "unit_contribution_xof": p - variable,
                    "unit_contribution_after_commission_xof": (p - variable - ((p * rate + 9999) // 10000 + commission_fixed)),
                    "below_variable_cost": p < variable,
                } for p in alternatives],
                "evidence": {"source_ref": source_ref, "observed_at": observed_at},
                "limitations": ["Taxes, returns, payment fees and other costs are excluded unless included in supplied costs.",
                                "Verified payment fields are asserted by the data provider; this module does not reconcile payment-provider records.",
                                "Targets are planning scenarios, not forecasts or realized revenue."],
            })
        except (RevenueOptimizationError, TypeError, KeyError) as exc:
            rejected.append({"index": index, "reason": str(exc)})
    return {
        "status": "available" if results else "no_valid_revenue_observations",
        "source": "explicit_user_supplied_offer_and_sales_observations",
        "observations_received": len(observations), "offers_analyzed": len(results),
        "offers_rejected": len(rejected), "offers": results, "rejected": rejected,
        "controls": {"read_only": True, "prices_changed": 0, "payments_processed": 0,
                     "commissions_paid": 0, "spending_xof": 0, "external_actions": 0},
    }
