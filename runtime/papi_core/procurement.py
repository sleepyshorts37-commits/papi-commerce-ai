"""Read-only supplier comparison and procurement proposal preparation."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

class ProcurementError(ValueError):
    """Invalid supplier/product observation."""

REQUIRED = {"supplier_id", "supplier_name", "product_key", "product_name", "market", "currency", "unit_price_xof", "minimum_order_quantity", "observed_at", "source_ref"}
OPTIONAL = {"shipping_total_xof", "shipping_allocation_units", "taxes_total_xof", "packaging_per_unit_xof", "other_fees_total_xof", "lead_time_days", "stock_status", "payment_terms", "completed_orders", "on_time_orders", "inspected_units", "defective_units", "documented_disputes"}

def _label(value: Any, field: str, limit: int = 180) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ProcurementError(f"{field} doit être un texte non vide ({limit} caractères maximum).")
    value = value.strip()
    if "@" in value or any(x in value.lower() for x in ("password", "token=", "api_key", "secret")):
        raise ProcurementError(f"{field} contient une donnée sensible interdite.")
    return value

def _integer(value: Any, field: str, *, optional: bool = False) -> int | None:
    if value is None and optional: return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ProcurementError(f"{field} doit être un entier positif ou nul.")
    return value

def _date(value: Any) -> datetime:
    if not isinstance(value, str): raise ProcurementError("observed_at doit être une date ISO 8601 avec fuseau.")
    try: parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc: raise ProcurementError("observed_at invalide.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None: raise ProcurementError("observed_at doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)

def _https(value: Any) -> str:
    ref = _label(value, "source_ref", 500); parsed = urlparse(ref)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ProcurementError("source_ref doit être une URL HTTPS publique sans identifiants.")
    return ref

def analyze_procurement(observations: list[dict[str, Any]], *, as_of: str | None = None, stale_after_days: int = 30) -> dict[str, Any]:
    """Compare explicitly supplied observations; does not browse, contact or purchase."""
    if not isinstance(observations, list): raise ProcurementError("observations doit être une liste.")
    now = _date(as_of) if as_of else datetime.now(timezone.utc)
    if isinstance(stale_after_days, bool) or not isinstance(stale_after_days, int) or stale_after_days < 1:
        raise ProcurementError("stale_after_days doit être un entier supérieur à zéro.")
    results, rejected, seen = [], [], set()
    for index, raw in enumerate(observations):
        try:
            if not isinstance(raw, dict) or not REQUIRED.issubset(raw) or set(raw) - REQUIRED - OPTIONAL:
                raise ProcurementError("Champs obligatoires manquants ou champs inconnus.")
            row = {k: _label(raw[k], k) for k in ("supplier_id", "supplier_name", "product_key", "product_name", "market")}
            if raw["currency"] != "XOF": raise ProcurementError("Seule la devise XOF est acceptée.")
            row["currency"] = "XOF"
            row["unit_price_xof"] = _integer(raw["unit_price_xof"], "unit_price_xof")
            row["minimum_order_quantity"] = _integer(raw["minimum_order_quantity"], "minimum_order_quantity")
            if row["unit_price_xof"] <= 0 or row["minimum_order_quantity"] <= 0:
                raise ProcurementError("Le prix et la quantité minimale doivent être strictement positifs.")
            observed = _date(raw["observed_at"]); row["observed_at"] = observed.isoformat().replace("+00:00", "Z")
            row["source_ref"] = _https(raw["source_ref"])
            for f in ("shipping_total_xof", "shipping_allocation_units", "taxes_total_xof", "packaging_per_unit_xof", "other_fees_total_xof", "lead_time_days", "completed_orders", "on_time_orders", "inspected_units", "defective_units", "documented_disputes"):
                row[f] = _integer(raw.get(f), f, optional=True)
            if row["shipping_total_xof"] is not None and (not row["shipping_allocation_units"] or row["shipping_allocation_units"] <= 0):
                raise ProcurementError("shipping_allocation_units est obligatoire avec les frais de livraison.")
            if row["shipping_total_xof"] is None and row["shipping_allocation_units"] is not None:
                raise ProcurementError("shipping_allocation_units nécessite shipping_total_xof.")
            if row["on_time_orders"] is not None and (row["completed_orders"] is None or row["on_time_orders"] > row["completed_orders"]):
                raise ProcurementError("Les commandes à temps doivent être comprises dans les commandes terminées.")
            if row["defective_units"] is not None and (row["inspected_units"] is None or row["defective_units"] > row["inspected_units"]):
                raise ProcurementError("Les unités défectueuses doivent être comprises dans les unités inspectées.")
            if row["documented_disputes"] is not None and row["completed_orders"] is not None and row["documented_disputes"] > row["completed_orders"]:
                raise ProcurementError("Les litiges documentés dépassent les commandes terminées.")
            for f in ("stock_status", "payment_terms"): row[f] = _label(raw[f], f) if raw.get(f) is not None else None
            key = (row["supplier_id"], row["product_key"], row["market"], row["observed_at"], row["source_ref"])
            if key in seen: continue
            seen.add(key)
            age = max(0, int((now - observed).total_seconds() // 86400))
            row["evidence_age_days"] = age; row["evidence_status"] = "stale" if age > stale_after_days else "current"
            row["evidence_is_independently_verified"] = False
            costs = ("taxes_total_xof", "packaging_per_unit_xof", "other_fees_total_xof")
            complete = all(row[f] is not None for f in costs) and row["shipping_total_xof"] is not None
            shipping_unit = ((row["shipping_total_xof"] + row["shipping_allocation_units"] - 1) // row["shipping_allocation_units"]) if complete else None
            landed = row["unit_price_xof"] + shipping_unit + sum(row[f] for f in costs) if complete else None
            row["shipping_cost_per_unit_xof"] = shipping_unit; row["landed_unit_cost_xof"] = landed
            row["landed_cost_status"] = "complete_estimate" if complete else "incomplete_cost_components"
            row["on_time_rate_percent"] = round(row["on_time_orders"] / row["completed_orders"] * 100, 2) if row["completed_orders"] and row["on_time_orders"] is not None else None
            row["defect_rate_percent"] = round(row["defective_units"] / row["inspected_units"] * 100, 2) if row["inspected_units"] and row["defective_units"] is not None else None
            row["reliability_status"] = "evidence_available" if any(row[f] is not None for f in ("on_time_rate_percent", "defect_rate_percent", "documented_disputes")) else "unknown"
            row["limitations"] = ["Source URL is supplied, not fetched or independently authenticated.", "Supplier identity, stock, prices, delivery times and reliability are not independently verified.", "Landed cost is an estimate based on supplied cost components."]
            results.append(row)
        except (ProcurementError, TypeError, KeyError) as exc: rejected.append({"index": index, "reason": str(exc)})
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in results:
        if row["evidence_status"] == "current" and row["landed_unit_cost_xof"] is not None:
            groups.setdefault((row["product_key"].casefold(), row["market"].casefold()), []).append(row)
    comparisons = []
    for (product, market), rows in sorted(groups.items()):
        ordered = sorted(rows, key=lambda r: (r["landed_unit_cost_xof"], r["lead_time_days"] if r["lead_time_days"] is not None else 10**9, r["supplier_id"]))
        comparisons.append({"product_key": product, "market": market, "ranking_basis": "estimated_landed_unit_cost_then_lead_time",
            "suppliers": [{"supplier_id": r["supplier_id"], "supplier_name": r["supplier_name"], "landed_unit_cost_xof": r["landed_unit_cost_xof"], "lead_time_days": r["lead_time_days"], "reliability_status": r["reliability_status"]} for r in ordered]})
    return {"status": "available" if results else "no_valid_supplier_observations", "source": "explicit_user_supplied_supplier_observations",
        "observations_received": len(observations), "observations_analyzed": len(results), "observations_rejected": len(rejected),
        "observations": results, "comparisons": comparisons, "rejected": rejected,
        "controls": {"read_only": True, "live_supplier_searches": 0, "suppliers_contacted": 0, "purchase_orders_created": 0, "purchases_executed": 0, "spending_xof": 0, "external_requests": 0}}
