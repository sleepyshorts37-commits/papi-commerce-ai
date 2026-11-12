"""Read-only stock ledger projection, availability and replenishment alerts."""
from __future__ import annotations
from datetime import datetime
from typing import Any

KINDS = {"receipt", "sale", "return", "adjustment_in", "adjustment_out", "reserve", "release"}

class InventoryError(ValueError):
    """Invalid inventory input."""

def _text(v: Any, field: str, limit: int = 160) -> str:
    if not isinstance(v, str) or not v.strip() or len(v.strip()) > limit:
        raise InventoryError(f"{field} doit être un texte non vide ({limit} caractères maximum).")
    value=v.strip()
    if "@" in value or any(x in value.lower() for x in ("password","token=","api_key","secret")):
        raise InventoryError(f"{field} contient une donnée sensible interdite.")
    return value

def _qty(v: Any, field: str, *, zero: bool = False) -> int:
    if isinstance(v,bool) or not isinstance(v,int) or v < (0 if zero else 1):
        raise InventoryError(f"{field} doit être un entier {'positif ou nul' if zero else 'strictement positif'}.")
    return v

def _timestamp(v: Any) -> str:
    if not isinstance(v,str): raise InventoryError("occurred_at doit être une date ISO 8601 avec fuseau.")
    try: dt=datetime.fromisoformat(v.replace("Z","+00:00"))
    except ValueError as exc: raise InventoryError("occurred_at invalide.") from exc
    if dt.tzinfo is None or dt.utcoffset() is None: raise InventoryError("occurred_at doit inclure un fuseau horaire.")
    return dt.isoformat().replace("+00:00","Z")

def build_inventory_control(movements: list[dict[str, Any]], *,
                            opening_stock: dict[str,int] | None = None,
                            reorder_points: dict[str,int] | None = None,
                            target_stock: dict[str,int] | None = None) -> dict[str, Any]:
    """Project supplied stock movements. No stock mutation, ordering or fulfillment occurs."""
    if not isinstance(movements,list): raise InventoryError("movements doit être une liste.")
    opening_stock=opening_stock or {}; reorder_points=reorder_points or {}; target_stock=target_stock or {}
    if not all(isinstance(x,dict) for x in (opening_stock,reorder_points,target_stock)):
        raise InventoryError("Les paramètres de stock doivent être des objets SKU:quantité.")
    opening={_text(k,"sku"): _qty(v,"opening_stock",zero=True) for k,v in opening_stock.items()}
    reorder={_text(k,"sku"): _qty(v,"reorder_point",zero=True) for k,v in reorder_points.items()}
    targets={_text(k,"sku"): _qty(v,"target_stock",zero=True) for k,v in target_stock.items()}
    if set(targets)-set(reorder): raise InventoryError("Chaque target_stock nécessite un reorder_point.")
    if any(targets[k]<reorder[k] for k in targets): raise InventoryError("target_stock doit être supérieur ou égal au reorder_point.")
    balances={sku:{"on_hand":qty,"reserved":0} for sku,qty in opening.items()}
    rows=[]; rejected=[]; seen=set()
    for i,raw in enumerate(movements):
        try:
            required={"movement_id","sku","product_name","location","kind","quantity","occurred_at"}
            optional={"reference"}
            if not isinstance(raw,dict) or not required.issubset(raw) or set(raw)-required-optional:
                raise InventoryError("Champs obligatoires manquants ou champs inconnus.")
            mid=_text(raw["movement_id"],"movement_id"); sku=_text(raw["sku"],"sku")
            name=_text(raw["product_name"],"product_name"); location=_text(raw["location"],"location")
            kind=_text(raw["kind"],"kind")
            if kind not in KINDS: raise InventoryError("kind non reconnu.")
            qty=_qty(raw["quantity"],"quantity")
            occurred=_timestamp(raw["occurred_at"])
            ref=_text(raw["reference"],"reference") if raw.get("reference") is not None else None
            if mid in seen: raise InventoryError("movement_id déjà utilisé.")
            seen.add(mid)
            bal=balances.setdefault(sku,{"on_hand":0,"reserved":0})
            next_on=bal["on_hand"]; next_res=bal["reserved"]
            if kind in {"receipt","return","adjustment_in"}: next_on+=qty
            elif kind in {"sale","adjustment_out"}: next_on-=qty
            elif kind=="reserve": next_res+=qty
            elif kind=="release": next_res-=qty
            if next_on<0: raise InventoryError("Stock physique insuffisant pour cette sortie.")
            if next_res<0: raise InventoryError("Réservation à libérer supérieure au stock réservé.")
            if next_res>next_on: raise InventoryError("Réservations supérieures au stock physique disponible.")
            bal["on_hand"]=next_on; bal["reserved"]=next_res
            rows.append({"movement_id":mid,"sku":sku,"product_name":name,"location":location,
                         "kind":kind,"quantity":qty,"occurred_at":occurred,"reference":ref})
        except (InventoryError,TypeError,KeyError) as exc: rejected.append({"index":i,"reason":str(exc)})
    all_skus=sorted(set(balances)|set(reorder)|set(targets))
    stock={}
    alerts=[]
    for sku in all_skus:
        bal=balances.get(sku,{"on_hand":0,"reserved":0})
        available=bal["on_hand"]-bal["reserved"]
        point=reorder.get(sku)
        target=targets.get(sku)
        status="not_configured" if point is None else ("reorder_required" if available<=point else "sufficient")
        suggestion=max(0,target-available) if target is not None and status=="reorder_required" else 0
        stock[sku]={"on_hand":bal["on_hand"],"reserved":bal["reserved"],"available":available,
                    "reorder_point":point,"target_stock":target,"status":status,
                    "suggested_replenishment_quantity":suggestion}
        if status=="reorder_required":
            alerts.append({"sku":sku,"available":available,"reorder_point":point,
                           "suggested_replenishment_quantity":suggestion,
                           "action":"manual_review_required_no_order_created"})
    return {"status":"available" if rows or opening or reorder else "no_inventory_data",
            "source":"user_supplied_inventory_movements_and_opening_balances",
            "movements_received":len(movements),"movements_analyzed":len(rows),
            "movements_rejected":len(rejected),"movements":rows,"rejected":rejected,
            "stock_by_sku":stock,"replenishment_alerts":alerts,
            "controls":{"read_only":True,"stock_records_written":0,"orders_created":0,
                        "supplier_contacts":0,"sales_fulfilled":0,"stock_adjustments_executed":0,
                        "spending_xof":0,"external_requests":0},
            "limitations":["Movements and opening balances are user-supplied and not independently verified.",
                           "SKU-level stock is aggregated across locations; location-level bin accounting is not implemented.",
                           "Suggested replenishment quantities are planning signals, not purchase orders."]}
