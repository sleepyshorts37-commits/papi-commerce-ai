"""Product sourcing and unit-economics intelligence from supplied evidence."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse


class ProductIntelligenceError(ValueError):
    """Product or supplier observation is invalid."""


COST_FIELDS = ("purchase_cost_xof", "shipping_cost_xof", "tax_cost_xof",
               "packaging_cost_xof", "platform_fee_xof")
SOURCE_TYPES = {"official_supplier_page", "public_catalog", "public_marketplace",
                "public_ad", "user_quote", "user_observation"}


def _text(value: Any, field: str, limit: int = 250) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ProductIntelligenceError(f"{field} doit être un texte non vide ({limit} caractères maximum).")
    cleaned = value.strip()
    if "@" in cleaned or any(token in cleaned.lower() for token in ("password", "token=", "api_key")):
        raise ProductIntelligenceError(f"{field} contient une donnée sensible interdite.")
    return cleaned


def _amount(value: Any, field: str, *, required: bool = False) -> int | None:
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ProductIntelligenceError(f"{field} doit être un entier XOF positif ou null.")
    return value


def _date(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ProductIntelligenceError("observed_at doit être une date ISO 8601.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProductIntelligenceError("observed_at invalide.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ProductIntelligenceError("observed_at doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)


def _https_url(value: Any) -> str:
    url = _text(value, "source_url", 1000)
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ProductIntelligenceError("source_url doit être une URL HTTPS publique sans identifiants.")
    if parsed.hostname.lower() in {"localhost", "127.0.0.1", "::1"}:
        raise ProductIntelligenceError("Les URL locales sont interdites.")
    return url


def analyze_product_options(
    observations: list[dict[str, Any]], *, as_of: str,
    target_selling_price_xof: int | None = None, freshness_days: int = 30,
) -> dict[str, Any]:
    """Estime les coûts unitaires et marges sans inventer les postes manquants."""
    if not isinstance(observations, list):
        raise ProductIntelligenceError("observations doit être une liste.")
    if isinstance(freshness_days, bool) or not isinstance(freshness_days, int) or not 1 <= freshness_days <= 365:
        raise ProductIntelligenceError("freshness_days doit être compris entre 1 et 365.")
    target_price = _amount(target_selling_price_xof, "target_selling_price_xof")
    now = _date(as_of)
    analyzed, rejected, seen = [], [], set()
    for index, raw in enumerate(observations):
        try:
            if not isinstance(raw, dict):
                raise ProductIntelligenceError("L'observation doit être un objet.")
            required = {"product_name", "market", "supplier_name", "source_type",
                        "source_url", "observed_at", "purchase_cost_xof"}
            optional = set(COST_FIELDS[1:]) | {"selling_price_xof", "currency",
                                                "minimum_order_quantity", "delivery_days", "notes"}
            if not required.issubset(raw) or set(raw) - required - optional:
                raise ProductIntelligenceError("Champs manquants ou inconnus.")
            product = _text(raw["product_name"], "product_name")
            market = _text(raw["market"], "market")
            supplier = _text(raw["supplier_name"], "supplier_name")
            source_type = _text(raw["source_type"], "source_type")
            if source_type not in SOURCE_TYPES:
                raise ProductIntelligenceError("source_type non reconnu.")
            source_url = _https_url(raw["source_url"])
            observed = _date(raw["observed_at"])
            if observed > now:
                raise ProductIntelligenceError("Observation datée dans le futur.")
            if raw.get("currency", "XOF") != "XOF":
                raise ProductIntelligenceError("Seuls les coûts explicitement exprimés en XOF sont acceptés.")
            costs = {field: _amount(raw.get(field), field, required=(field == "purchase_cost_xof"))
                     for field in COST_FIELDS}
            selling = _amount(raw.get("selling_price_xof"), "selling_price_xof")
            moq = raw.get("minimum_order_quantity")
            delivery = raw.get("delivery_days")
            for value, field in ((moq, "minimum_order_quantity"), (delivery, "delivery_days")):
                if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                    raise ProductIntelligenceError(f"{field} doit être un entier positif ou null.")
            notes = raw.get("notes", "")
            if not isinstance(notes, str) or len(notes) > 500 or "@" in notes:
                raise ProductIntelligenceError("notes invalide ou contenant une donnée personnelle.")
            key = (product.casefold(), market.casefold(), supplier.casefold(),
                   source_url, observed.isoformat())
            if key in seen:
                continue
            seen.add(key)
            known = [value for value in costs.values() if value is not None]
            complete_cost = all(value is not None for value in costs.values())
            landed = sum(known) if complete_cost else None
            price = selling if selling is not None else target_price
            gross_profit = price - landed if price is not None and landed is not None else None
            margin_pct = round(gross_profit / price * 100, 2) if gross_profit is not None and price and price > 0 else None
            age = (now - observed).days
            analyzed.append({
                "product_name": product, "market": market, "supplier_name": supplier,
                "source_type": source_type, "source_url": source_url,
                "observed_at": observed.isoformat().replace("+00:00", "Z"),
                "age_days": age, "fresh": age <= freshness_days,
                "currency": "XOF", **costs,
                "known_cost_subtotal_xof": sum(known),
                "fully_loaded_unit_cost_xof": landed,
                "cost_estimate_complete": complete_cost,
                "selling_price_xof": price,
                "selling_price_source": "observation" if selling is not None else ("user_target" if target_price is not None else "unknown"),
                "gross_profit_per_unit_xof": gross_profit,
                "gross_margin_percent": margin_pct,
                "minimum_order_quantity": moq, "delivery_days": delivery,
                "notes": notes,
                "evidence_status": "source_reference_provided_not_fetched_or_verified",
                "recommendation": ("evaluate_sample_and_supplier" if complete_cost and gross_profit is not None and gross_profit > 0 and age <= freshness_days
                                   else "collect_missing_costs_or_verify_source"),
            })
        except (ProductIntelligenceError, TypeError, KeyError) as exc:
            rejected.append({"index": index, "reason": str(exc)})
    analyzed.sort(key=lambda row: (not row["fresh"], row["fully_loaded_unit_cost_xof"] is None,
                                   row["fully_loaded_unit_cost_xof"] or 0,
                                   row["product_name"].casefold(), row["supplier_name"].casefold()))
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in analyzed:
        groups.setdefault((row["product_name"].casefold(), row["market"].casefold()), []).append(row)
    comparisons = []
    for rows in groups.values():
        comparable = [row for row in rows if row["fully_loaded_unit_cost_xof"] is not None]
        comparisons.append({
            "product_name": rows[0]["product_name"], "market": rows[0]["market"],
            "supplier_observations": len(rows),
            "comparable_supplier_costs_xof": [row["fully_loaded_unit_cost_xof"] for row in comparable],
            "lowest_observed_fully_loaded_cost_xof": min((row["fully_loaded_unit_cost_xof"] for row in comparable), default=None),
            "supplier_names": [row["supplier_name"] for row in rows],
            "comparison_limit": "Only complete XOF unit-cost breakdowns are ranked; product specifications and supplier terms still require human equivalence checks.",
        })
    return {
        "status": "available" if analyzed else "no_valid_product_observations",
        "source": "user_supplied_supplier_and_product_observations",
        "observations_received": len(observations),
        "observations_analyzed": len(analyzed),
        "observations_rejected": len(rejected),
        "products": analyzed,
        "supplier_comparisons": comparisons,
        "limitations": [
            "No supplier URL is visited or independently verified.",
            "A complete cost requires purchase, shipping, tax, packaging and platform fees.",
            "A positive estimated margin is not proof of demand, sell-through or net profitability.",
            "Product quality, authenticity, customs, returns, warranties and delivery terms require human verification.",
        ],
        "controls": {"network_requests": 0, "pages_fetched": 0, "supplier_contacts": 0,
                     "purchases": 0, "spending_xof": 0, "actions_executed": 0, "read_only": True},
    }
