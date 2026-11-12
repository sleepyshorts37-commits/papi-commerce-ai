"""PAPI inventory and supplier registry: validated, read-only stock snapshots."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

SUPPLIER_FIELDS={"supplier_id","display_name","category","status","lead_time_days","payment_terms"}
PRODUCT_FIELDS={"product_id","sku","display_name","supplier_id","unit_cost_xof","reorder_level","status"}
MOVEMENT_FIELDS={"movement_id","product_id","kind","quantity","occurred_at","reference"}
SUPPLIER_STATUSES={"prospect","approved","suspended"}
PRODUCT_STATUSES={"active","inactive"}
MOVEMENT_KINDS={"in","out","adjustment"}

def _text(value: Any, field: str) -> str:
    if not isinstance(value,str) or not value.strip() or len(value)>120:
        raise ValueError(f"{field} invalide.")
    return value.strip()

def _nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value,bool) or not isinstance(value,int) or value<0:
        raise ValueError(f"{field} doit être un entier positif ou nul.")
    return value

def _timestamp(value: Any) -> datetime:
    if not isinstance(value,str) or not value:
        raise ValueError("occurred_at doit être une date ISO 8601.")
    try: dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc: raise ValueError("occurred_at invalide.") from exc
    if dt.tzinfo is None: raise ValueError("occurred_at doit inclure un fuseau horaire.")
    return dt.astimezone(timezone.utc)

def _record(raw: Any, allowed: set[str], required: set[str], label: str) -> dict:
    if not isinstance(raw,dict): raise ValueError(f"{label} doit être un objet.")
    if set(raw)-allowed: raise ValueError(f"Champ non autorisé dans {label}.")
    if not required.issubset(raw): raise ValueError(f"Champ obligatoire manquant dans {label}.")
    return raw

def analyze_inventory(suppliers: list[dict], products: list[dict], movements: list[dict], *, as_of: str|None=None) -> dict:
    """Analyze supplied snapshots only. Never contacts suppliers or changes stock."""
    if any(not isinstance(x,list) or len(x)>1000 for x in (suppliers,products,movements)):
        raise ValueError("Chaque catégorie doit être une liste de 1 000 éléments maximum.")
    now=_timestamp(as_of or datetime.now(timezone.utc).isoformat())
    clean_suppliers=[]; clean_products=[]; clean_movements=[]; rejected=[]
    def add(rows, raw_rows, validator, category):
        seen=set()
        for i,raw in enumerate(raw_rows):
            try:
                item=validator(raw)
                key=item[next(iter(item))] if False else item["_key"]
                if key in seen: raise ValueError("Identifiant dupliqué.")
                seen.add(key); item.pop("_key"); rows.append(item)
            except (ValueError,TypeError,KeyError) as exc:
                rejected.append({"category":category,"index":i,"reason":str(exc)})
    def supplier(raw):
        x=_record(raw,SUPPLIER_FIELDS,{"supplier_id","display_name","category","status","lead_time_days","payment_terms"},"fournisseur")
        if x["status"] not in SUPPLIER_STATUSES: raise ValueError("Statut fournisseur inconnu.")
        return {"_key":_text(x["supplier_id"],"supplier_id"),"supplier_id":_text(x["supplier_id"],"supplier_id"),
                "display_name":_text(x["display_name"],"display_name"),"category":_text(x["category"],"category"),
                "status":x["status"],"lead_time_days":_nonnegative_int(x["lead_time_days"],"lead_time_days"),
                "payment_terms":_text(x["payment_terms"],"payment_terms")}
    add(clean_suppliers,suppliers,supplier,"supplier")
    supplier_ids={x["supplier_id"] for x in clean_suppliers}
    def product(raw):
        x=_record(raw,PRODUCT_FIELDS,{"product_id","sku","display_name","supplier_id","unit_cost_xof","reorder_level","status"},"produit")
        if x["supplier_id"] not in supplier_ids: raise ValueError("Fournisseur inconnu.")
        if x["status"] not in PRODUCT_STATUSES: raise ValueError("Statut produit inconnu.")
        return {"_key":_text(x["product_id"],"product_id"),"product_id":_text(x["product_id"],"product_id"),
                "sku":_text(x["sku"],"sku"),"display_name":_text(x["display_name"],"display_name"),
                "supplier_id":x["supplier_id"],"unit_cost_xof":_nonnegative_int(x["unit_cost_xof"],"unit_cost_xof"),
                "reorder_level":_nonnegative_int(x["reorder_level"],"reorder_level"),"status":x["status"]}
    add(clean_products,products,product,"product")
    product_ids={x["product_id"] for x in clean_products}
    def movement(raw):
        x=_record(raw,MOVEMENT_FIELDS,{"movement_id","product_id","kind","quantity","occurred_at","reference"},"mouvement")
        mid=_text(x["movement_id"],"movement_id"); pid=_text(x["product_id"],"product_id")
        if pid not in product_ids: raise ValueError("Produit inconnu.")
        if x["kind"] not in MOVEMENT_KINDS: raise ValueError("Type de mouvement inconnu.")
        qty=_nonnegative_int(x["quantity"],"quantity")
        if qty==0: raise ValueError("La quantité doit être supérieure à zéro.")
        dt=_timestamp(x["occurred_at"])
        if dt>now: raise ValueError("Mouvement daté dans le futur.")
        return {"_key":mid,"movement_id":mid,"product_id":pid,"kind":x["kind"],"quantity":qty,
                "occurred_at":dt.isoformat(),"reference":_text(x["reference"],"reference")}
    add(clean_movements,movements,movement,"movement")
    stock={p["product_id"]:0 for p in clean_products}
    for m in sorted(clean_movements,key=lambda x:x["occurred_at"]):
        if m["kind"]=="in": stock[m["product_id"]]+=m["quantity"]
        elif m["kind"]=="out": stock[m["product_id"]]-=m["quantity"]
        else: stock[m["product_id"]]=m["quantity"]
    by_id={p["product_id"]:p for p in clean_products}
    balances=[{"product_id":pid,"sku":by_id[pid]["sku"],"display_name":by_id[pid]["display_name"],
               "supplier_id":by_id[pid]["supplier_id"],"quantity_on_hand":qty,
               "reorder_level":by_id[pid]["reorder_level"],
               "low_stock":by_id[pid]["status"]=="active" and qty<=by_id[pid]["reorder_level"]}
              for pid,qty in sorted(stock.items())]
    return {"as_of":now.isoformat(),"counts":{"suppliers":len(clean_suppliers),"products":len(clean_products),
            "movements":len(clean_movements),"rejected_records":len(rejected)},
            "stock":{"balances":balances,"low_stock_product_ids":[x["product_id"] for x in balances if x["low_stock"]],
            "negative_stock_product_ids":[x["product_id"] for x in balances if x["quantity_on_hand"]<0]},
            "suppliers":{"approved":sum(x["status"]=="approved" for x in clean_suppliers),
            "prospects":sum(x["status"]=="prospect" for x in clean_suppliers),
            "suspended":sum(x["status"]=="suspended" for x in clean_suppliers)},
            "rejected":rejected,"safety":{"read_only":True,"external_actions":False,
            "purchase_orders":False,"financial_actions":False,"budget_xof":0,"human_approval_required":True}}
