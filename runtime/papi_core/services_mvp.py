"""PAPI SERVICES MVP: read-only service funnel and verified-receipt tracking."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

REQUEST_STATUSES={"new","qualified","quoted","accepted","declined","cancelled"}
QUOTE_STATUSES={"draft","sent_for_human_dispatch","accepted","rejected","expired"}
WORK_STATUSES={"not_started","in_progress","waiting_client","delivered","cancelled"}
PAYMENT_STATUSES={"unpaid","declared_paid","provider_verified","refunded"}
REQUEST_FIELDS={"request_id","service_code","scope_summary","status","created_at"}
QUOTE_FIELDS={"quote_id","request_id","amount_xof","currency","valid_until","status"}
WORK_FIELDS={"work_id","quote_id","status","started_at","updated_at","delivered_at"}
PAYMENT_FIELDS={"payment_id","work_id","amount_xof","currency","status","evidence_ref","verified_by","verified_at"}

def _date(value: Any, field: str) -> datetime:
    if not isinstance(value,str) or not value: raise ValueError(f"{field} doit être une date ISO 8601.")
    try: parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc: raise ValueError(f"{field} doit être une date ISO 8601.") from exc
    if parsed.tzinfo is None: raise ValueError(f"{field} doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)

def _id(value: Any, field: str) -> str:
    if not isinstance(value,str) or not value.strip() or len(value)>100: raise ValueError(f"{field} invalide.")
    return value.strip()

def _amount(value: Any) -> int:
    if isinstance(value,bool) or not isinstance(value,int) or value<=0: raise ValueError("amount_xof doit être un entier strictement positif.")
    return value

def _fields(raw: Any, allowed: set[str], required: set[str], label: str) -> dict:
    if not isinstance(raw,dict): raise ValueError(f"Chaque {label} doit être un objet.")
    if set(raw)-allowed: raise ValueError(f"Champs non autorisés dans {label} : données personnelles ou champ inconnu.")
    if not required.issubset(raw): raise ValueError(f"Champs obligatoires manquants dans {label}.")
    return raw

def _request(raw: Any) -> dict:
    x=_fields(raw,REQUEST_FIELDS,{"request_id","service_code","scope_summary","status","created_at"},"demande")
    summary=x["scope_summary"]
    if not isinstance(summary,str) or not summary.strip() or len(summary)>1000: raise ValueError("scope_summary invalide.")
    if x["status"] not in REQUEST_STATUSES: raise ValueError("Statut de demande inconnu.")
    return {"request_id":_id(x["request_id"],"request_id"),"service_code":_id(x["service_code"],"service_code"),
            "scope_summary":summary.strip(),"status":x["status"],"created_at":_date(x["created_at"],"created_at").isoformat()}

def _quote(raw: Any, request_ids: set[str], now: datetime) -> dict:
    x=_fields(raw,QUOTE_FIELDS,{"quote_id","request_id","amount_xof","valid_until","status"},"devis")
    qid,rid=_id(x["quote_id"],"quote_id"),_id(x["request_id"],"request_id")
    if rid not in request_ids: raise ValueError("Le devis référence une demande inconnue.")
    if x.get("currency","XOF")!="XOF": raise ValueError("Seule la devise XOF est acceptée.")
    if x["status"] not in QUOTE_STATUSES: raise ValueError("Statut de devis inconnu.")
    until=_date(x["valid_until"],"valid_until")
    return {"quote_id":qid,"request_id":rid,"amount_xof":_amount(x["amount_xof"]),"currency":"XOF",
            "valid_until":until.isoformat(),"status":x["status"],
            "is_expired":x["status"] not in {"accepted","rejected"} and until<now}

def _work(raw: Any, quote_ids: set[str]) -> dict:
    x=_fields(raw,WORK_FIELDS,{"work_id","quote_id","status","started_at","updated_at"},"prestation")
    wid,qid=_id(x["work_id"],"work_id"),_id(x["quote_id"],"quote_id")
    if qid not in quote_ids: raise ValueError("La prestation référence un devis inconnu.")
    if x["status"] not in WORK_STATUSES: raise ValueError("Statut de prestation inconnu.")
    start,updated=_date(x["started_at"],"started_at"),_date(x["updated_at"],"updated_at")
    if updated<start: raise ValueError("updated_at ne peut pas précéder started_at.")
    delivered=_date(x["delivered_at"],"delivered_at") if x.get("delivered_at") else None
    if delivered and not start<=delivered<=updated: raise ValueError("delivered_at doit être compris entre started_at et updated_at.")
    if x["status"]=="delivered" and delivered is None: raise ValueError("Une prestation livrée doit avoir delivered_at.")
    return {"work_id":wid,"quote_id":qid,"status":x["status"],"started_at":start.isoformat(),
            "updated_at":updated.isoformat(),"delivered_at":delivered.isoformat() if delivered else None}

def _payment(raw: Any, work_ids: set[str]) -> dict:
    x=_fields(raw,PAYMENT_FIELDS,{"payment_id","work_id","amount_xof","status"},"paiement")
    pid,wid=_id(x["payment_id"],"payment_id"),_id(x["work_id"],"work_id")
    if wid not in work_ids: raise ValueError("Le paiement référence une prestation inconnue.")
    if x["status"] not in PAYMENT_STATUSES: raise ValueError("Statut de paiement inconnu.")
    if x.get("currency","XOF")!="XOF": raise ValueError("Seule la devise XOF est acceptée.")
    amount=_amount(x["amount_xof"])
    evidence,verifier,verified_at=x.get("evidence_ref"),x.get("verified_by"),x.get("verified_at")
    verified=None
    if x["status"]=="provider_verified":
        _id(evidence,"evidence_ref"); _id(verifier,"verified_by")
        verified=_date(verified_at,"verified_at")
    elif verified_at: verified=_date(verified_at,"verified_at")
    return {"payment_id":pid,"work_id":wid,"amount_xof":amount,"currency":"XOF","status":x["status"],
            "evidence_ref":evidence,"verified_by":verifier,"verified_at":verified.isoformat() if verified else None,
            "recognized_revenue_xof":amount if x["status"]=="provider_verified" else 0}

def analyze_services(requests: list[dict], quotes: list[dict], work_items: list[dict],
                     payments: list[dict], *, as_of: str|None=None) -> dict:
    """Analyze minimized snapshots; never contacts clients or performs financial actions."""
    groups=(requests,quotes,work_items,payments)
    if any(not isinstance(g,list) for g in groups): raise ValueError("Les quatre catégories doivent être des listes.")
    if any(len(g)>500 for g in groups): raise ValueError("Maximum de 500 enregistrements par catégorie.")
    now=_date(as_of or datetime.now(timezone.utc).isoformat(),"as_of")
    clean=[[],[],[],[]]; rejected=[]
    validators=[_request,None,None,None]
    labels=["demande","devis","prestation","paiement"]
    idkeys=["request_id","quote_id","work_id","payment_id"]
    for idx,raw in enumerate(requests):
        try:
            if isinstance(raw,dict) and raw.get("request_id") in {v["request_id"] for v in clean[0]}: raise ValueError("request_id dupliqué.")
            clean[0].append(_request(raw))
        except (ValueError,TypeError,KeyError) as e: rejected.append({"category":"demande","index":idx,"reason":str(e)})
    request_ids={x["request_id"] for x in clean[0]}
    for idx,raw in enumerate(quotes):
        try:
            if isinstance(raw,dict) and raw.get("quote_id") in {v["quote_id"] for v in clean[1]}: raise ValueError("quote_id dupliqué.")
            clean[1].append(_quote(raw,request_ids,now))
        except (ValueError,TypeError,KeyError) as e: rejected.append({"category":"devis","index":idx,"reason":str(e)})
    quote_ids={x["quote_id"] for x in clean[1]}
    for idx,raw in enumerate(work_items):
        try:
            if isinstance(raw,dict) and raw.get("work_id") in {v["work_id"] for v in clean[2]}: raise ValueError("work_id dupliqué.")
            clean[2].append(_work(raw,quote_ids))
        except (ValueError,TypeError,KeyError) as e: rejected.append({"category":"prestation","index":idx,"reason":str(e)})
    work_ids={x["work_id"] for x in clean[2]}
    for idx,raw in enumerate(payments):
        try:
            if isinstance(raw,dict) and raw.get("payment_id") in {v["payment_id"] for v in clean[3]}: raise ValueError("payment_id dupliqué.")
            clean[3].append(_payment(raw,work_ids))
        except (ValueError,TypeError,KeyError) as e: rejected.append({"category":"paiement","index":idx,"reason":str(e)})
    revenue=sum(x["recognized_revenue_xof"] for x in clean[3])
    return {"as_of":now.isoformat(),"counts":{"requests":len(clean[0]),"quotes":len(clean[1]),"work_items":len(clean[2]),"payments":len(clean[3]),"rejected_records":len(rejected)},
      "funnel":{"new_requests":sum(x["status"] in {"new","qualified"} for x in clean[0]),
        "quotes_accepted":sum(x["status"]=="accepted" for x in clean[1]),
        "work_in_progress":sum(x["status"] in {"not_started","in_progress","waiting_client"} for x in clean[2]),
        "work_delivered":sum(x["status"]=="delivered" for x in clean[2])},
      "revenue":{"recognized_xof":revenue,"verified_payment_count":sum(x["status"]=="provider_verified" for x in clean[3]),
        "unverified_declared_xof":sum(x["amount_xof"] for x in clean[3] if x["status"]=="declared_paid"),
        "note":"Les attestations provider_verified doivent être contrôlées sur la source du prestataire."},
      "rejected":rejected,"safety":{"read_only":True,"external_actions":False,"financial_actions":False,"budget_xof":0,"human_approval_required":True}}
