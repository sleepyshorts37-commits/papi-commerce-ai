"""Registre financier append-only : aucun mouvement bancaire n'est exécuté."""
from __future__ import annotations
import json, os, re
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
FINANCE_FILE=ROOT/"data"/"finance"/"entries.jsonl"
ID_RE=re.compile(r"^[a-z0-9][a-z0-9_-]{1,79}$")
KINDS={"income","expense","refund","fee"}
STATUSES={"income":{"pending_verification","verified","rejected"},"expense":{"proposed","approved","paid","rejected"},"refund":{"pending_verification","verified","rejected"},"fee":{"proposed","approved","paid","rejected"}}
SENSITIVE=re.compile(r"(password|secret|token|otp|pin|cvv|card_number|iban|account_number|phone|email|address|customer_data)",re.I)

class FinanceError(ValueError):
    """Entrée financière invalide ou registre incohérent."""

def _date(value: Any) -> bool:
    if not isinstance(value,str): return False
    try: return datetime.fromisoformat(value.replace("Z","+00:00")).tzinfo is not None
    except ValueError: return False

def validate_entry(entry: Any) -> list[str]:
    errors=[]
    if not isinstance(entry,dict): return ["Une écriture doit être un objet."]
    required={"id","kind","status","amount_xof","occurred_at","description","reference"}
    allowed=required|{"provider","verification","approval","related_entry_id","category","payment_evidence"}
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
        v=entry.get("verification")
        if not isinstance(v,dict) or not all(isinstance(v.get(k),str) and v[k].strip() for k in ("method","evidence_reference","verified_by","verified_at")) or not _date(v.get("verified_at")):
            errors.append("Un revenu/remboursement vérifié exige méthode, référence de preuve, vérificateur et date.")
    if kind in {"expense","fee"} and entry.get("status") in {"approved","paid"}:
        a=entry.get("approval")
        if not isinstance(a,dict) or not all(isinstance(a.get(k),str) and a[k].strip() for k in ("approved_by","approval_reference","approved_at")) or not _date(a.get("approved_at")):
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
    for i,e in enumerate(data["entries"]):
        for error in validate_entry(e): errors.append(f"entries[{i}]: {error}")
        if not isinstance(e,dict): continue
        if e.get("id") in ids: errors.append(f"Identifiant dupliqué: {e.get('id')}.")
        ids.add(e.get("id"))
        if e.get("reference") in refs: errors.append("Référence interne dupliquée.")
        refs.add(e.get("reference"))
        v=e.get("verification")
        if isinstance(v,dict):
            proof=v.get("evidence_reference")
            if proof and proof in seen: errors.append("Référence de preuve de paiement dupliquée.")
            if proof: seen.add(proof)
    for i,e in enumerate(data["entries"]):
        if isinstance(e,dict) and e.get("kind")=="refund" and e.get("related_entry_id") not in ids:
            errors.append(f"entries[{i}]: écriture d'origine inconnue.")
    return errors

def load_ledger(path: Path=FINANCE_FILE) -> dict[str,Any]:
    target=Path(path); entries=[]
    if target.exists():
        try:
            for number,line in enumerate(target.read_text(encoding="utf-8").splitlines(),1):
                if not line.strip(): continue
                try: entries.append(json.loads(line))
                except json.JSONDecodeError as exc: raise FinanceError(f"Écriture JSON invalide ligne {number}.") from exc
        except OSError as exc: raise FinanceError("Impossible de lire le registre financier.") from exc
    data={"project":"PAPI COMMERCE AI","currency":"XOF","entries":entries,"policy":"Append-only financial event log."}
    errors=validate_ledger(data)
    if errors: raise FinanceError("; ".join(errors))
    return data

def append_entry(entry: dict[str,Any], path: Path=FINANCE_FILE) -> bool:
    """Ajoute une écriture validée sans modifier l'historique ; écrivain unique uniquement."""
    errors=validate_entry(entry)
    if errors: raise FinanceError("; ".join(errors))
    data=load_ledger(path)
    for old in data["entries"]:
        if old["id"]==entry["id"]:
            if old==entry: return False
            raise FinanceError("Identifiant déjà utilisé avec un contenu différent.")
        if old["reference"]==entry["reference"]: raise FinanceError("Référence interne déjà utilisée.")
    errors=validate_ledger({**data,"entries":[*data["entries"],entry]})
    if errors: raise FinanceError("; ".join(errors))
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    payload=(json.dumps(entry,ensure_ascii=False,sort_keys=True)+"\n").encode("utf-8")
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
    try: os.write(fd,payload); os.fsync(fd)
    finally: os.close(fd)
    return True

def finance_report(path: Path=FINANCE_FILE) -> dict[str,Any]:
    entries=load_ledger(path)["entries"]
    income=sum(e["amount_xof"] for e in entries if e["kind"]=="income" and e["status"]=="verified")
    refunds=sum(e["amount_xof"] for e in entries if e["kind"]=="refund" and e["status"]=="verified")
    expenses=sum(e["amount_xof"] for e in entries if e["kind"]=="expense" and e["status"]=="paid")
    fees=sum(e["amount_xof"] for e in entries if e["kind"]=="fee" and e["status"]=="paid")
    pending=sum(e["amount_xof"] for e in entries if e["kind"] in {"income","refund"} and e["status"]=="pending_verification")
    return {"mode":"read_only_local","currency":"XOF","entries_total":len(entries),
      "verified_income_xof":income,"verified_refunds_xof":refunds,"paid_expenses_xof":expenses,
      "paid_fees_xof":fees,"net_verified_cashflow_xof":income-refunds-expenses-fees,
      "pending_verification_xof":pending,"autonomous_payments_enabled":False,
      "note":"Prévision, demande ou paiement non vérifié ne constitue pas une recette encaissée."}
