"""Registre commercial local : validation et rapports, sans prospection externe."""
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SALES_FILE = ROOT / "data" / "sales.json"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,79}$")
STATUSES = {
 "prospect":{"new","qualified","contact_prepared","contacted","replied","customer","lost","opted_out"},
 "opportunity":{"identified","assessing","approved_for_pilot","rejected","won","lost"},
 "offer":{"draft","active","paused","retired"},
 "deal":{"lead","discovery","proposal","negotiation","won","lost"},
 "interaction":{"note","draft_prepared","approval_requested","approved","sent_verified","response_logged"},
}
ACTIVITIES={"PAPI MARKET","PAPI DROPSHIPPING","PAPI AFFILIATION","PAPI FREELANCE","PAPI SERVICES","PAPI BUSINESS PARTNERS"}
SENSITIVE_KEYS={"password","token","access_token","secret","otp","pin","cvv","card_number"}

class SalesError(ValueError):
    """Données commerciales invalides."""

def _nonempty(value: Any) -> bool:
    return isinstance(value,str) and bool(value.strip())

def _valid_id(value: Any) -> bool:
    return isinstance(value,str) and bool(ID_RE.fullmatch(value))

def _contains_sensitive_key(value: Any) -> bool:
    if isinstance(value,dict):
        return any(str(k).casefold() in SENSITIVE_KEYS or _contains_sensitive_key(v) for k,v in value.items())
    if isinstance(value,list):
        return any(_contains_sensitive_key(v) for v in value)
    return False

def validate_sales(data: dict[str,Any]) -> list[str]:
    errors=[]
    collections=("prospects","opportunities","offers","pipeline","interactions")
    if not isinstance(data,dict):
        return ["Le registre commercial doit être un objet."]
    if data.get("project") != "PAPI COMMERCE AI":
        errors.append("project doit être PAPI COMMERCE AI.")
    if set(data)-{"project",*collections}:
        errors.append("Le registre contient des sections inconnues.")
    if _contains_sensitive_key(data):
        errors.append("Champ sensible interdit dans le registre.")
    seen={name:set() for name in collections}
    for name in collections:
        records=data.get(name)
        if not isinstance(records,list):
            errors.append(f"{name} doit être une liste."); continue
        for i,item in enumerate(records):
            label=f"{name}[{i}]"
            if not isinstance(item,dict):
                errors.append(f"{label} doit être un objet."); continue
            rid=item.get("id")
            if not _valid_id(rid): errors.append(f"{label}: identifiant invalide.")
            elif rid in seen[name]: errors.append(f"{label}: identifiant dupliqué.")
            else: seen[name].add(rid)
            if name=="prospects":
                if not _nonempty(item.get("name")) or not _nonempty(item.get("source")): errors.append(f"{label}: name et source publique obligatoires.")
                if item.get("status") not in STATUSES["prospect"]: errors.append(f"{label}: statut prospect invalide.")
                if not isinstance(item.get("opt_out",False),bool): errors.append(f"{label}: opt_out doit être booléen.")
                if item.get("opt_out") and item.get("status")!="opted_out": errors.append(f"{label}: opt_out impose le statut opted_out.")
            elif name=="opportunities":
                if item.get("activity") not in ACTIVITIES or not _nonempty(item.get("problem")): errors.append(f"{label}: activité ou problème invalide.")
                if item.get("status") not in STATUSES["opportunity"]: errors.append(f"{label}: statut opportunité invalide.")
                for field in ("estimated_value_xof","estimated_cost_xof","confidence_pct"):
                    value=item.get(field)
                    if isinstance(value,bool) or not isinstance(value,(int,float)) or value<0: errors.append(f"{label}: {field} doit être positif ou nul.")
                if isinstance(item.get("confidence_pct"),(int,float)) and item["confidence_pct"]>100: errors.append(f"{label}: confidence_pct ne peut dépasser 100.")
            elif name=="offers":
                if item.get("activity") not in ACTIVITIES or not _nonempty(item.get("name")): errors.append(f"{label}: activité ou nom d'offre invalide.")
                if item.get("status") not in STATUSES["offer"]: errors.append(f"{label}: statut offre invalide.")
                for field in ("price_xof","direct_cost_xof"):
                    value=item.get(field)
                    if isinstance(value,bool) or not isinstance(value,(int,float)) or value<0: errors.append(f"{label}: {field} doit être positif ou nul.")
            elif name=="pipeline":
                if not _valid_id(item.get("prospect_id")) or not _valid_id(item.get("offer_id")): errors.append(f"{label}: prospect_id et offer_id invalides.")
                if item.get("status") not in STATUSES["deal"]: errors.append(f"{label}: étape de vente invalide.")
                amount=item.get("amount_xof"); probability=item.get("probability_pct")
                if isinstance(amount,bool) or not isinstance(amount,(int,float)) or amount<0: errors.append(f"{label}: amount_xof invalide.")
                if isinstance(probability,bool) or not isinstance(probability,(int,float)) or not 0<=probability<=100: errors.append(f"{label}: probability_pct doit être entre 0 et 100.")
            elif name=="interactions":
                if not _valid_id(item.get("prospect_id")) or item.get("type") not in STATUSES["interaction"]: errors.append(f"{label}: prospect_id ou type invalide.")
                if item.get("external_action") is True and item.get("approval_status")!="approved": errors.append(f"{label}: action externe sans approbation explicite.")
                if item.get("type")=="sent_verified" and not item.get("evidence"): errors.append(f"{label}: une interaction envoyée exige une preuve.")
    prospects=seen["prospects"]; offers=seen["offers"]
    for i,deal in enumerate(data.get("pipeline",[]) if isinstance(data.get("pipeline"),list) else []):
        if isinstance(deal,dict):
            if deal.get("prospect_id") not in prospects: errors.append(f"pipeline[{i}]: prospect inconnu.")
            if deal.get("offer_id") not in offers: errors.append(f"pipeline[{i}]: offre inconnue.")
    for i,note in enumerate(data.get("interactions",[]) if isinstance(data.get("interactions"),list) else []):
        if isinstance(note,dict) and note.get("prospect_id") not in prospects: errors.append(f"interactions[{i}]: prospect inconnu.")
    return errors

def load_sales(path: Path=SALES_FILE) -> dict[str,Any]:
    try: data=json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise SalesError("Impossible de lire le registre commercial.") from exc
    errors=validate_sales(data)
    if errors: raise SalesError("; ".join(errors))
    return data

def build_sales_report(path: Path=SALES_FILE) -> dict[str,Any]:
    data=load_sales(path)
    active=[o for o in data["offers"] if o["status"]=="active"]
    return {
      "mode":"read_only_local","prospects_total":len(data["prospects"]),
      "prospects_opted_out":sum(bool(p.get("opt_out")) for p in data["prospects"]),
      "opportunities_total":len(data["opportunities"]),"offers_active":len(active),
      "active_offer_margin_xof":sum(o["price_xof"]-o["direct_cost_xof"] for o in active),
      "pipeline_total":len(data["pipeline"]),
      "pipeline_weighted_value_xof":round(sum(d["amount_xof"]*d["probability_pct"]/100 for d in data["pipeline"] if d["status"] not in {"won","lost"}),2),
      "interactions_total":len(data["interactions"]),"verified_revenue_xof":0,
      "revenue_note":"Aucun revenu reconnu ici ; comptabilité et vérification des paiements séparées.",
      "external_actions_enabled":False
    }
