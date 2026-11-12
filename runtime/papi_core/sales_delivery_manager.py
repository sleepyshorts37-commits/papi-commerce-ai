"""Read-only sales and delivery reconciliation from anonymized snapshots."""
from datetime import datetime, timezone
from typing import Any

SALE_FIELDS={"sale_id","order_id","business_unit","amount_xof","currency","payment_status","created_at"}
DELIVERY_FIELDS={"delivery_id","order_id","status","created_at","updated_at","delivered_at","failure_code"}
SALE_STATUSES={"unpaid","payment_declared","provider_attested","refunded"}
DELIVERY_STATUSES={"pending","assigned","picked_up","delivered","failed","returned"}

def _date(v: Any,n: str)->datetime:
    if not isinstance(v,str) or not v: raise ValueError(f"{n} doit être une date ISO 8601.")
    try: d=datetime.fromisoformat(v.replace("Z","+00:00"))
    except ValueError as e: raise ValueError(f"{n} invalide.") from e
    if d.tzinfo is None: raise ValueError(f"{n} doit inclure un fuseau horaire.")
    d=d.astimezone(timezone.utc)
    if d>datetime.now(timezone.utc): raise ValueError(f"{n} ne peut pas être dans le futur.")
    return d

def _id(v: Any,n: str)->str:
    if not isinstance(v,str) or not v.strip() or len(v)>100: raise ValueError(f"{n} invalide.")
    return v.strip()

def _amount(v: Any)->int:
    if isinstance(v,bool) or not isinstance(v,int) or v<=0: raise ValueError("amount_xof doit être un entier positif.")
    return v

def analyze_sales_delivery(sales: list[dict], deliveries: list[dict])->dict:
    if not isinstance(sales,list) or not isinstance(deliveries,list) or len(sales)>1000 or len(deliveries)>2000:
        raise ValueError("Listes invalides ou trop volumineuses.")
    valid_sales=[]; valid_ids=set(); rejected=[]
    for i,x in enumerate(sales):
        try:
            if not isinstance(x,dict) or set(x)-SALE_FIELDS or not SALE_FIELDS.issubset(x): raise ValueError("Structure de vente invalide ou donnée personnelle interdite.")
            sid=_id(x["sale_id"],"sale_id"); oid=_id(x["order_id"],"order_id")
            if sid in {s["sale_id"] for s in valid_sales}: raise ValueError("sale_id dupliqué.")
            if x["payment_status"] not in SALE_STATUSES: raise ValueError("Statut de paiement inconnu.")
            if x.get("currency","XOF")!="XOF": raise ValueError("Seule la devise XOF est acceptée.")
            valid_sales.append({"sale_id":sid,"order_id":oid,"business_unit":_id(x["business_unit"],"business_unit"),
                "amount_xof":_amount(x["amount_xof"]),"payment_status":x["payment_status"],"created_at":_date(x["created_at"],"created_at").isoformat()})
            valid_ids.add(oid)
        except (ValueError,TypeError,KeyError) as e: rejected.append({"category":"sale","index":i,"reason":str(e)})
    valid_deliveries=[]; seen=set()
    for i,x in enumerate(deliveries):
        try:
            if not isinstance(x,dict) or set(x)-DELIVERY_FIELDS or not {"delivery_id","order_id","status","created_at","updated_at"}.issubset(x): raise ValueError("Structure de livraison invalide ou donnée personnelle interdite.")
            did=_id(x["delivery_id"],"delivery_id"); oid=_id(x["order_id"],"order_id")
            if did in seen: raise ValueError("delivery_id dupliqué.")
            seen.add(did)
            if oid not in valid_ids: raise ValueError("Aucune vente valide ne référence cette commande.")
            status=x["status"]
            if status not in DELIVERY_STATUSES: raise ValueError("Statut de livraison inconnu.")
            created=_date(x["created_at"],"created_at"); updated=_date(x["updated_at"],"updated_at")
            if updated<created: raise ValueError("updated_at précède created_at.")
            delivered=_date(x["delivered_at"],"delivered_at") if x.get("delivered_at") else None
            if delivered and not created<=delivered<=updated: raise ValueError("delivered_at hors période.")
            if status=="delivered" and delivered is None: raise ValueError("Livraison livrée sans delivered_at.")
            failure=x.get("failure_code")
            if status=="failed":
                failure=_id(failure,"failure_code")
                if len(failure)>40: raise ValueError("failure_code trop long.")
            elif failure is not None: raise ValueError("failure_code réservé aux livraisons échouées.")
            valid_deliveries.append({"delivery_id":did,"order_id":oid,"status":status,"created_at":created.isoformat(),
                "updated_at":updated.isoformat(),"delivered_at":delivered.isoformat() if delivered else None,"failure_code":failure})
        except (ValueError,TypeError,KeyError) as e: rejected.append({"category":"delivery","index":i,"reason":str(e)})
    sale_by_order={s["order_id"]:s for s in valid_sales}
    delivered_ids={d["order_id"] for d in valid_deliveries if d["status"]=="delivered"}
    counts={s:sum(d["status"]==s for d in valid_deliveries) for s in sorted(DELIVERY_STATUSES)}
    declared=sum(s["amount_xof"] for s in valid_sales if s["payment_status"]=="payment_declared")
    attested=sum(s["amount_xof"] for s in valid_sales if s["payment_status"]=="provider_attested")
    return {"counts":{"sales":len(valid_sales),"deliveries":len(valid_deliveries),"rejected_records":len(rejected),
        "deliveries_by_status":counts,"sales_with_delivery":len({d["order_id"] for d in valid_deliveries}),
        "delivered_orders":len(delivered_ids),"sales_without_delivery":len(valid_ids-{d["order_id"] for d in valid_deliveries})},
        "financial":{"gross_declared_sales_xof":sum(s["amount_xof"] for s in valid_sales),
        "unpaid_sales_xof":sum(s["amount_xof"] for s in valid_sales if s["payment_status"]=="unpaid"),
        "payment_declared_xof":declared,"provider_attested_xof":attested,
        "recognized_revenue_xof":0,"note":"Les statuts et attestations sont fournis par l'opérateur et ne sont pas authentifiés par un prestataire de paiement."},
        "sales":valid_sales,"deliveries":valid_deliveries,"rejected":rejected,
        "safety":{"read_only":True,"customer_contact":False,"courier_dispatch":False,"payments_or_refunds":False,
        "inventory_mutation":False,"external_actions":False,"budget_xof":0,"human_review_required":True}}
