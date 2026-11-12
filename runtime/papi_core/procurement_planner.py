"""Human-reviewed replenishment planning; no purchasing side effects."""
from typing import Any
PRODUCT_FIELDS={"product_id","sku","display_name","supplier_id","quantity_on_hand","reorder_level","target_stock","unit_cost_xof","status"}
SUPPLIER_FIELDS={"supplier_id","display_name","status","lead_time_days","minimum_order_quantity"}
def _int(v: Any,n: str)->int:
    if isinstance(v,bool) or not isinstance(v,int) or v<0: raise ValueError(f"{n} invalide.")
    return v
def _text(v: Any,n: str)->str:
    if not isinstance(v,str) or not v.strip() or len(v)>120: raise ValueError(f"{n} invalide.")
    return v.strip()
def plan_replenishment(products: list[dict], suppliers: list[dict], *, budget_xof: int=0)->dict:
    if not isinstance(products,list) or not isinstance(suppliers,list) or len(products)>1000 or len(suppliers)>1000: raise ValueError("Listes invalides.")
    budget=_int(budget_xof,"budget_xof"); sm={}; rejected=[]
    for i,x in enumerate(suppliers):
        try:
            if not isinstance(x,dict) or set(x)-SUPPLIER_FIELDS or not SUPPLIER_FIELDS.issubset(x): raise ValueError("Structure fournisseur invalide.")
            sid=_text(x["supplier_id"],"supplier_id")
            if sid in sm: raise ValueError("Fournisseur dupliqué.")
            if x["status"] not in {"approved","prospect","suspended"}: raise ValueError("Statut invalide.")
            sm[sid]={"name":_text(x["display_name"],"display_name"),"status":x["status"],"lead":_int(x["lead_time_days"],"lead_time_days"),"moq":_int(x["minimum_order_quantity"],"minimum_order_quantity")}
        except (ValueError,TypeError,KeyError) as e: rejected.append({"category":"supplier","index":i,"reason":str(e)})
    proposals=[]; seen=set()
    for i,x in enumerate(products):
        try:
            if not isinstance(x,dict) or set(x)-PRODUCT_FIELDS or not PRODUCT_FIELDS.issubset(x): raise ValueError("Structure produit invalide.")
            pid=_text(x["product_id"],"product_id")
            if pid in seen: raise ValueError("Produit dupliqué.")
            seen.add(pid); sid=_text(x["supplier_id"],"supplier_id")
            if sid not in sm: raise ValueError("Fournisseur inconnu.")
            if x["status"] not in {"active","inactive"}: raise ValueError("Statut produit invalide.")
            current=_int(x["quantity_on_hand"],"quantity_on_hand"); reorder=_int(x["reorder_level"],"reorder_level")
            target=_int(x["target_stock"],"target_stock"); cost=_int(x["unit_cost_xof"],"unit_cost_xof")
            if target<reorder: raise ValueError("Cible inférieure au seuil.")
            s=sm[sid]; qty=max(0,target-current) if x["status"]=="active" and current<=reorder and s["status"]=="approved" else 0
            if qty and s["moq"]: qty=max(qty,s["moq"])
            if qty: proposals.append({"product_id":pid,"sku":_text(x["sku"],"sku"),"display_name":_text(x["display_name"],"display_name"),"supplier_id":sid,"supplier_name":s["name"],"suggested_quantity":qty,"unit_cost_xof":cost,"estimated_total_xof":qty*cost,"lead_time_days":s["lead"],"within_configured_budget":qty*cost<=budget,"decision":"awaiting_human_approval"})
        except (ValueError,TypeError,KeyError) as e: rejected.append({"category":"product","index":i,"reason":str(e)})
    proposals.sort(key=lambda x:(not x["within_configured_budget"],x["lead_time_days"],x["estimated_total_xof"],x["product_id"]))
    return {"proposals":proposals,"counts":{"products_received":len(products),"suppliers_received":len(suppliers),"proposals":len(proposals),"rejected_records":len(rejected)},"estimated_total_xof":sum(x["estimated_total_xof"] for x in proposals),"rejected":rejected,"safety":{"read_only":True,"purchase_orders_created":False,"supplier_contact":False,"payments":False,"stock_mutation":False,"budget_xof":budget,"external_actions":False,"human_approval_required":True}}
