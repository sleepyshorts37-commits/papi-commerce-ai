"""Registre financier append-only : aucun mouvement bancaire n'est exécuté."""
from __future__ import annotations
import json, os, re
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
FINANCE_FILE=ROOT/"data"/"finance-ledger.json"
ID_RE=re.compile(r"^[a-z0-9][a-z0-9_-]{1,79}$")
KINDS={"income","expense","refund","fee"}
STATUSES={"income":{"pending_verification","verified","rejected"},"expense":{"proposed","approved","paid","rejected"},"refund":{"pending_verification","verified","rejected"},"fee":{"proposed","approved","paid","rejected"}}
SENSITIVE=re.compile(r"(password|secret|token|otp|pin|cvv|card_number|iban|account_number|phone|email|address|customer_data)",re.I)

class FinanceError(ValueError):
    """Entrée financière invalide ou registre incohérent."""

def _date(value: Any) -> bool:
    if not isinstance(value,str): return False
    try:
        parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
        return parsed.tzinfo is not None
    except ValueError: return False

def validate_entry(entry: Any) -> list[str]:
    errors=[]
    if not isinstance(entry,dict): return ["Une écriture doit être un objet."]
    required={"id","kind","status","amount_xof","occurred_at","description","reference"}
    allowed=required|{"provider","verification","approval","related_entry_id","category"}
    if required-entry.keys(): errors.append("Champs obligatoires manquants.")
    if entry.keys()-allowed: errors.append("Champs inconnus dans l'écriture.")
    def scan(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if SENSITIVE.search(str(key)): errors.append("Champ financier sensible interdit.")
                scan(item)
        elif isinstance(value,list):
            for item in value: scan(item)
    scan(entry)
    if not isinstance(entry.get("id"),str) or not ID_RE.fullmatch(entry.get("id","")): errors.append("id invalide.")
    kind=entry.get("kind")
    if kind not in KINDS: errors.append("kind doit être income, expense, refund ou fee.")
    if kind in KINDS and entry.get("status") not in STATUSES[kind]: errors.append("Statut incompatible avec le type.")
    amount=entry.get("amount_xof")
    if isinstance(amount,bool) or not isinstance(amount,int) or amount<=0: errors.append("amount_xof doit être un entier XOF strictement positif.")
    if not _date(entry.get("occurred_at")): errors.append("occurred_at doit être une date ISO 8601 avec fuseau.")
    if not isinstance(entry.get("description"),str) or not entry.get("description","").strip() or len(entry.get("description",""))>240: errors.append("description invalide.")
    if not isinstance(entry.get("reference"),str) or not entry.get("reference","").strip() or len(entry.get("reference",""))>120: errors.append("reference interne obligatoire.")
    if kind in {"income","refund"} and entry.get("status")=="verified":
        verification=entry.get("verification")
        if not isinstance(verification,dict) or not all(isinstance(verification.get(k),str) and verification[k].strip() for k in ("method","evidence_reference","verified_by","verified_at")) or not _date(verification.get("verified_at")):
            errors.append("Un revenu/remboursement vérifié exige méthode, référence de preuve, vérificateur et date.")
    if kind in {"expense","fee"} and entry.get("status") in {"approved","paid"}:
        approval=entry.get("approval")
        if not isinstance(approval,dict) or not all(isinstance(approval.get(k),str) and approval[k].strip() for k in ("approved_by","approval_reference","approved_at")) or not _date(approval.get("approved_at")):
            errors.append("Une dépense approuvée/payée exige une approbation tracée.")
    if kind in {"expense","fee"} and entry.get("status")=="paid" and not isinstance(entry.get("payment_evidence"),str):
        errors.append("Une dépense payée exige une référence de preuve de paiement.")
    if kind=="refund" and not (isinstance(entry.get("related_entry_id"),str) and ID_RE.fullmatch(entry.get("related_entry_id",""))):
        errors.append("Un remboursement doit référencer l'écriture d'origine.")
    return errors

def validate_ledger(data: Any) -> list[str]:
    if not isinstance(data,dict) or data.get("project")!="PAPI COMMERCE AI" or data.get("currency")!="XOF" or not isinstance(data.get("entries"),list):
        return ["Structure du registre financier invalide."]
    errors=[]; seen=set(); refs=set(); ids=set()
    for i,entry in enumerate(data["entries"]):
        for error in validate_entry(entry): errors.append(f"entries[{i}]: {error}")
        if not isinstance(entry,dict): continue
        eid=entry.get("id")
        if eid in ids: errors.append(f"Identifiant dupliqué: {eid}.")
        ids.add(eid)
        ref=entry.get("reference")
        if ref in refs: errors.append(f"Référence interne dupliquée: {ref}.")
        refs.add(ref)
        provider=entry.get("provider")
        verification=entry.get("verification")
        if isinstance(verification,dict):
            evidence=verification.get("evidence_reference")
            if evidence in seen: errors.append("Référence de preuve de paiement dupliquée.")
            if evidence: seen.add(evidence)
    for i,entry in enumerate(data["entries"]):
        if isinstance(entry,dict) and entry.get("kind")=="refund" and entry.get("related_entry_id") not in ids:
            errors.append(f"entries[{i}]: écriture d'origine inconnue.")
    return errors

def load_ledger(path: Path=FINANCE_FILE) -> dict[str,Any]:
    try: data=json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise FinanceError("Impossible de lire le registre financier.") from exc
    errors=validate_ledger(data)
    if errors: raise FinanceError("; ".join(errors))
    return data

def append_entry(entry: dict[str,Any], path: Path=FINANCE_FILE) -> bool:
    """Ajoute une écriture validée sans modifier l'historique ; écrivain unique uniquement."""
    errors=validate_entry(entry)
    if errors: raise FinanceError("; ".join(errors))
    data=load_ledger(path)
    if any(old["id"]==entry["id"] for old in data["entries"]): return False
    if any(old["reference"]==entry["reference"] for old in data["entries"]): raise FinanceError("Référence interne déjà utilisée.")
    updated={**data,"entries":[*data["entries"],entry]}
    errors=validate_ledger(updated)
    if errors: raise FinanceError("; ".join(errors))
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    payload=(json.dumps(entry,ensure_ascii=False,sort_keys=True)+"\n").encode("utf-8")
    fd=os.open(target,os.O_WRONLY|os.O_APPEND)
    try: os.write(fd,payload); os.fsync(fd)
    finally: os.close(fd)
    return True

def finance_report(path: Path=FINANCE_FILE) -> dict[str,Any]:
    data=load_ledger(path); entries=data["entries"]
    verified_income=sum(e["amount_xof"] for e in entries if e["kind"]=="income" and e["status"]=="verified")
    verified_refunds=sum(e["amount_xof"] for e in entries if e["kind"]=="refund" and e["status"]=="verified")
    paid_expenses=sum(e["amount_xof"] for e in entries if e["kind"]=="expense" and e["status"]=="paid")
    paid_fees=sum(e["amount_xof"] for e in entries if e["kind"]=="fee" and e["status"]=="paid")
    pending=sum(e["amount_xof"] for e in entries if e["kind"] in {"income","refund"} and e["status"]=="pending_verification")
    return {"mode":"read_only_local","currency":"XOF","entries_total":len(entries),
      "verified_income_xof":verified_income,"verified_refunds_xof":verified_refunds,
      "paid_expenses_xof":paid_expenses,"paid_fees_xof":paid_fees,
      "net_verified_cashflow_xof":verified_income-verified_refunds-paid_expenses-paid_fees,
      "pending_verification_xof":pending,"autonomous_payments_enabled":False,
      "note":"Prévision, demande ou paiement non vérifié ne constitue pas une recette encaissée."}
