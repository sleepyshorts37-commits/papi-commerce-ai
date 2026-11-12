"""Read-only executive dashboard over precomputed PAPI module snapshots."""
from typing import Any
def _snapshot(value:Any,name:str)->dict:
    if value is None: return {}
    if not isinstance(value,dict): raise ValueError(f"Snapshot {name} invalide.")
    return value
def build_executive_dashboard(*,sales_delivery:dict|None=None,financial:dict|None=None,inventory:dict|None=None,procurement:dict|None=None,services:dict|None=None)->dict:
    sd=_snapshot(sales_delivery,"sales_delivery"); fin=_snapshot(financial,"financial")
    inv=_snapshot(inventory,"inventory"); proc=_snapshot(procurement,"procurement"); svc=_snapshot(services,"services")
    sd_counts=sd.get("counts",{}); fin_counts=fin.get("counts",{}); fin_totals=fin.get("declared_totals",{})
    fin_safety=fin.get("safety",{}); sales_fin=sd.get("financial",{})
    inv_counts=inv.get("counts",{}); proc_counts=proc.get("counts",{}); svc_counts=svc.get("counts",{})
    for name,obj in [("sales_delivery.counts",sd_counts),("financial.counts",fin_counts),("financial.declared_totals",fin_totals),("inventory.counts",inv_counts),("procurement.counts",proc_counts),("services.counts",svc_counts)]:
        if not isinstance(obj,dict): raise ValueError(f"Structure {name} invalide.")
    def number(obj,key):
        v=obj.get(key,0)
        if isinstance(v,bool) or not isinstance(v,(int,float)) or v<0: raise ValueError(f"Indicateur {key} invalide.")
        return v
    declared_in=number(fin_totals,"incoming_xof"); declared_out=number(fin_totals,"outgoing_xof")
    declared_sales=number(sales_fin,"gross_declared_sales_xof")
    return {"commercial":{"sales_records":number(sd_counts,"sales"),"delivery_records":number(sd_counts,"deliveries"),"delivered_orders":number(sd_counts,"delivered_orders"),"sales_without_delivery":number(sd_counts,"sales_without_delivery"),"service_requests":number(svc_counts,"requests"),"open_service_cases":number(svc_counts,"open_cases")},
      "finance":{"gross_declared_sales_xof":declared_sales,"declared_incoming_xof":declared_in,"declared_outgoing_xof":declared_out,"net_declared_cashflow_xof":declared_in-declared_out,"matched_transactions":number(fin_counts,"matched"),"unmatched_transactions":number(fin_counts,"unmatched_transactions"),"recognized_revenue_xof":0,"provider_authenticated":False},
      "operations":{"inventory_products":number(inv_counts,"products"),"low_stock_items":number(inv_counts,"low_stock"),"negative_stock_items":number(inv_counts,"negative_stock"),"replenishment_proposals":number(proc_counts,"proposals"),"rejected_records":sum(number(x,"rejected_records") for x in [sd_counts,fin_counts,inv_counts,proc_counts,svc_counts])},
      "data_quality":{"snapshots_supplied":sum(bool(x) for x in [sd,fin,inv,proc,svc]),"missing_snapshots":[n for n,x in [("sales_delivery",sd),("financial",fin),("inventory",inv),("procurement",proc),("services",svc)] if not x],"operator_supplied_data_only":True},
      "safety":{"read_only":True,"external_actions":False,"payments_or_transfers":False,"stock_mutation":False,"recognized_revenue_claimed":False,"budget_xof":0,"human_review_required":True,"note":"Agrégation de snapshots fournis; aucune synchronisation ni authentification indépendante."}}
