"""Read-only matching of declared transactions to supplied statement snapshots."""
from datetime import datetime, timezone
from typing import Any
TX_FIELDS={"transaction_id","reference","direction","amount_xof","status","occurred_at","source"}
ST_FIELDS={"statement_id","reference","direction","amount_xof","occurred_at"}
def _txt(v:Any,n:str)->str:
    if not isinstance(v,str) or not v.strip() or len(v)>120: raise ValueError(f"{n} invalide.")
    return v.strip()
def _amt(v:Any)->int:
    if isinstance(v,bool) or not isinstance(v,int) or v<=0: raise ValueError("Montant invalide.")
    return v
def _dt(v:Any,n:str)->datetime:
    if not isinstance(v,str): raise ValueError(f"{n} invalide.")
    try: d=datetime.fromisoformat(v.replace("Z","+00:00"))
    except ValueError as e: raise ValueError(f"{n} invalide.") from e
    if d.tzinfo is None: raise ValueError(f"{n} sans fuseau horaire.")
    d=d.astimezone(timezone.utc)
    if d>datetime.now(timezone.utc): raise ValueError(f"{n} dans le futur.")
    return d
def reconcile_finances(transactions:list[dict], statement_entries:list[dict])->dict:
    if not isinstance(transactions,list) or not isinstance(statement_entries,list) or len(transactions)>5000 or len(statement_entries)>5000: raise ValueError("Volumes invalides.")
    rejected=[]; txs=[]; seen=set()
    for i,x in enumerate(transactions):
        try:
            if not isinstance(x,dict) or set(x)-TX_FIELDS or not TX_FIELDS.issubset(x): raise ValueError("Structure transaction invalide ou champ personnel interdit.")
            tid=_txt(x["transaction_id"],"transaction_id")
            if tid in seen: raise ValueError("Identifiant transaction dupliqué.")
            seen.add(tid)
            if x["direction"] not in {"in","out"} or x["status"] not in {"declared","cancelled","refunded"}: raise ValueError("Direction ou statut invalide.")
            txs.append({"transaction_id":tid,"reference":_txt(x["reference"],"reference"),"direction":x["direction"],"amount_xof":_amt(x["amount_xof"]),"status":x["status"],"occurred_at":_dt(x["occurred_at"],"occurred_at"),"source":_txt(x["source"],"source")})
        except (ValueError,TypeError,KeyError) as e: rejected.append({"category":"transaction","index":i,"reason":str(e)})
    entries=[]; st_seen=set()
    for i,x in enumerate(statement_entries):
        try:
            if not isinstance(x,dict) or set(x)-ST_FIELDS or not ST_FIELDS.issubset(x): raise ValueError("Structure relevé invalide ou champ personnel interdit.")
            sid=_txt(x["statement_id"],"statement_id")
            if sid in st_seen: raise ValueError("Identifiant relevé dupliqué.")
            st_seen.add(sid)
            if x["direction"] not in {"in","out"}: raise ValueError("Direction invalide.")
            entries.append({"statement_id":sid,"reference":_txt(x["reference"],"reference"),"direction":x["direction"],"amount_xof":_amt(x["amount_xof"]),"occurred_at":_dt(x["occurred_at"],"occurred_at")})
        except (ValueError,TypeError,KeyError) as e: rejected.append({"category":"statement","index":i,"reason":str(e)})
    index={}
    for e in entries: index.setdefault((e["reference"],e["direction"],e["amount_xof"]),[]).append(e)
    matched=[]; unmatched=[]; used=set()
    for t in txs:
        key=(t["reference"],t["direction"],t["amount_xof"]); candidates=[e for e in index.get(key,[]) if e["statement_id"] not in used]
        if t["status"]!="declared":
            unmatched.append({"transaction_id":t["transaction_id"],"reason":"transaction_not_active"}); continue
        if len(candidates)==1:
            e=candidates[0]; used.add(e["statement_id"])
            matched.append({"transaction_id":t["transaction_id"],"statement_id":e["statement_id"],"reference":t["reference"],"amount_xof":t["amount_xof"],"direction":t["direction"],"date_difference_seconds":abs(int((t["occurred_at"]-e["occurred_at"]).total_seconds())),"match_basis":"reference_direction_amount"})
        elif len(candidates)>1: unmatched.append({"transaction_id":t["transaction_id"],"reason":"ambiguous_statement_match"})
        else: unmatched.append({"transaction_id":t["transaction_id"],"reason":"no_statement_match"})
    unmatched_statement=[e["statement_id"] for e in entries if e["statement_id"] not in used]
    incoming=sum(x["amount_xof"] for x in txs if x["status"]=="declared" and x["direction"]=="in")
    outgoing=sum(x["amount_xof"] for x in txs if x["status"]=="declared" and x["direction"]=="out")
    return {"counts":{"transactions":len(txs),"statement_entries":len(entries),"matched":len(matched),"unmatched_transactions":len(unmatched),"unmatched_statement_entries":len(unmatched_statement),"rejected_records":len(rejected)},
      "declared_totals":{"incoming_xof":incoming,"outgoing_xof":outgoing,"net_declared_xof":incoming-outgoing,"recognized_revenue_xof":0},
      "matched":matched,"unmatched_transactions":unmatched,"unmatched_statement_ids":unmatched_statement,"rejected":rejected,
      "safety":{"read_only":True,"provider_authentication":False,"bank_connection":False,"payments_or_transfers":False,"budget_xof":0,"external_actions":False,"human_review_required":True,"note":"Matching compares supplied snapshots only; it does not authenticate statement origin, transaction settlement, or revenue."}}
