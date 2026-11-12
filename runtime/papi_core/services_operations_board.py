"""PAPI SERVICES OPERATIONS BOARD 1.65: human-reviewed delivery queues."""
from __future__ import annotations
from datetime import datetime, timezone

REQUEST_FIELDS={"request_id","service_code","scope_summary","status","created_at"}
QUOTE_FIELDS={"quote_id","request_id","amount_xof","currency","valid_until","status"}
WORK_FIELDS={"work_id","quote_id","status","started_at","updated_at","delivered_at"}
PAYMENT_FIELDS={"payment_id","work_id","amount_xof","currency","status","evidence_ref","verified_by","verified_at"}

def _date(value, field):
    if not isinstance(value,str) or not value:
        raise ValueError(f"{field}: date ISO 8601 requise.")
    try: d=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc: raise ValueError(f"{field}: date invalide.") from exc
    if d.tzinfo is None: raise ValueError(f"{field}: fuseau horaire obligatoire.")
    return d.astimezone(timezone.utc)

def _rows(rows, allowed, required, label):
    if not isinstance(rows,list) or len(rows)>500:
        raise ValueError(f"{label}: liste requise (500 éléments maximum).")
    clean=[]; seen=set(); rejected=[]
    for i,row in enumerate(rows):
        try:
            if not isinstance(row,dict) or set(row)-allowed or not required.issubset(row):
                raise ValueError("Champs invalides, manquants ou non autorisés.")
            key=next(iter(required))
            # IDs are validated explicitly by the caller below.
            clean.append(dict(row))
        except (ValueError,TypeError,KeyError) as exc:
            rejected.append({"category":label,"index":i,"reason":str(exc)})
    return clean,rejected

def build_services_operations_board(*,requests,quotes,work_items,payments,as_of=None):
    """Create a read-only action queue; tasks are recommendations, never executions."""
    now=_date(as_of or datetime.now(timezone.utc).isoformat(),"as_of")
    req,rej1=_rows(requests,REQUEST_FIELDS,{"request_id","service_code","scope_summary","status","created_at"},"request")
    qts,rej2=_rows(quotes,QUOTE_FIELDS,{"quote_id","request_id","amount_xof","valid_until","status"},"quote")
    wrk,rej3=_rows(work_items,WORK_FIELDS,{"work_id","quote_id","status","started_at","updated_at"},"work")
    pay,rej4=_rows(payments,PAYMENT_FIELDS,{"payment_id","work_id","amount_xof","status"},"payment")
    rejected=rej1+rej2+rej3+rej4
    def unique(rows,key,label):
        seen=set(); out=[]
        for i,x in enumerate(rows):
            v=x.get(key)
            if not isinstance(v,str) or not v.strip() or len(v)>100 or v in seen:
                rejected.append({"category":label,"index":i,"reason":f"{key} invalide ou dupliqué."})
            else: seen.add(v); out.append(x)
        return out
    req=unique(req,"request_id","request"); qts=unique(qts,"quote_id","quote")
    wrk=unique(wrk,"work_id","work"); pay=unique(pay,"payment_id","payment")
    valid_requests={}
    for i,x in enumerate(req):
        try:
            if x["status"] not in {"new","qualified","quoted","accepted","declined","cancelled"}: raise ValueError("Statut de demande inconnu.")
            _date(x["created_at"],"created_at")
            if not isinstance(x["scope_summary"],str) or not x["scope_summary"].strip() or len(x["scope_summary"])>1000: raise ValueError("Résumé invalide.")
            valid_requests[x["request_id"]]=x
        except (ValueError,TypeError,KeyError) as e: rejected.append({"category":"request","index":i,"reason":str(e)})
    valid_quotes={}
    for i,x in enumerate(qts):
        try:
            if x["request_id"] not in valid_requests: raise ValueError("Demande liée inconnue ou invalide.")
            if x["status"] not in {"draft","sent_for_human_dispatch","accepted","rejected","expired"}: raise ValueError("Statut de devis inconnu.")
            if isinstance(x["amount_xof"],bool) or not isinstance(x["amount_xof"],int) or x["amount_xof"]<=0: raise ValueError("Montant XOF invalide.")
            if x.get("currency","XOF")!="XOF": raise ValueError("Devise non prise en charge.")
            expiry=_date(x["valid_until"],"valid_until")
            valid_quotes[x["quote_id"]]={**x,"_expired":expiry<now}
        except (ValueError,TypeError,KeyError) as e: rejected.append({"category":"quote","index":i,"reason":str(e)})
    valid_work={}
    for i,x in enumerate(wrk):
        try:
            q=valid_quotes.get(x["quote_id"])
            if not q or q["status"]!="accepted" or q["_expired"]: raise ValueError("Prestation sans devis accepté et valide.")
            if x["status"] not in {"not_started","in_progress","waiting_client","delivered","cancelled"}: raise ValueError("Statut de prestation inconnu.")
            start=_date(x["started_at"],"started_at"); updated=_date(x["updated_at"],"updated_at")
            if updated<start or updated>now: raise ValueError("Chronologie de prestation invalide.")
            delivered=_date(x["delivered_at"],"delivered_at") if x.get("delivered_at") else None
            if x["status"]=="delivered" and (delivered is None or not start<=delivered<=updated): raise ValueError("Date de livraison manquante ou invalide.")
            valid_work[x["work_id"]]=x
        except (ValueError,TypeError,KeyError) as e: rejected.append({"category":"work","index":i,"reason":str(e)})
    payments_by_work={}
    for i,x in enumerate(pay):
        try:
            if x["work_id"] not in valid_work: raise ValueError("Prestation liée inconnue ou invalide.")
            if x["status"] not in {"unpaid","declared_paid","provider_verified","refunded"}: raise ValueError("Statut de paiement inconnu.")
            if isinstance(x["amount_xof"],bool) or not isinstance(x["amount_xof"],int) or x["amount_xof"]<=0: raise ValueError("Montant XOF invalide.")
            if x.get("currency","XOF")!="XOF": raise ValueError("Devise non prise en charge.")
            if x["status"]=="provider_verified":
                if not all(isinstance(x.get(k),str) and x[k].strip() for k in ("evidence_ref","verified_by","verified_at")): raise ValueError("Attestation de paiement incomplète.")
                _date(x["verified_at"],"verified_at")
            payments_by_work.setdefault(x["work_id"],[]).append(x)
        except (ValueError,TypeError,KeyError) as e: rejected.append({"category":"payment","index":i,"reason":str(e)})
    quotes_by_request={}
    for q in valid_quotes.values(): quotes_by_request.setdefault(q["request_id"],[]).append(q)
    work_by_quote={}
    for w in valid_work.values(): work_by_quote.setdefault(w["quote_id"],[]).append(w)
    tasks=[]
    def task(kind,ref,priority,description):
        tasks.append({"task_id":f"{kind}:{ref}","type":kind,"reference":ref,"priority":priority,
                      "description":description,"status":"awaiting_human_review","external_action":False})
    for rid,r in valid_requests.items():
        related=quotes_by_request.get(rid,[])
        if r["status"] in {"new","qualified"} and not related:
            task("qualify_request",rid,1,"Préciser le besoin et préparer un devis; aucune communication automatique.")
        elif related and not any(q["status"]=="accepted" and not q["_expired"] for q in related) and r["status"] not in {"declined","cancelled"}:
            task("review_quote",rid,2,"Vérifier le devis, sa validité et la décision client avant toute suite.")
    for qid,q in valid_quotes.items():
        if q["status"]=="accepted" and not q["_expired"] and not work_by_quote.get(qid):
            task("schedule_delivery",qid,1,"Planifier la prestation après validation humaine du périmètre et de la capacité.")
    for wid,w in valid_work.items():
        linked=next(q for q in valid_quotes.values() if q["quote_id"]==w["quote_id"])
        if w["status"] in {"not_started","in_progress","waiting_client"}:
            task("deliver_service",wid,1,"Suivre et terminer la prestation; toute livraison doit être confirmée humainement.")
        elif w["status"]=="delivered":
            related=payments_by_work.get(wid,[])
            paid=sum(p["amount_xof"] for p in related if p["status"] in {"declared_paid","provider_verified"})
            if paid<linked["amount_xof"]:
                task("reconcile_payment",wid,2,"Comparer le paiement déclaré au devis et contrôler la preuve auprès du prestataire.")
            elif any(p["status"]=="provider_verified" for p in related):
                task("verify_provider_evidence",wid,2,"Contrôler indépendamment les attestations; les libellés fournis ne prouvent pas un encaissement.")
    tasks.sort(key=lambda x:(x["priority"],x["task_id"]))
    return {"as_of":now.isoformat(),"tasks":tasks,
      "counts":{"requests":len(valid_requests),"quotes":len(valid_quotes),"work_items":len(valid_work),
                "payments":sum(len(v) for v in payments_by_work.values()),"tasks_waiting_review":len(tasks),
                "rejected_records":len(rejected)},
      "rejected":rejected,
      "safety":{"read_only":True,"messages_sent":False,"external_contacts":False,"orders_created":False,
                "payments_or_transfers":False,"recognized_revenue_xof":0,"budget_xof":0,
                "human_approval_required":True,"note":"Tableau de tâches proposé à partir de snapshots fournis; aucune action n'est exécutée et les paiements ne sont pas authentifiés."}}
