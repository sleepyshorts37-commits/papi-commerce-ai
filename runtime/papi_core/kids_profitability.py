"""Evidence-based unit economics for zero-upfront PAPI KIDS channels."""
from __future__ import annotations
import json, re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from pathlib import Path
from typing import Any

MAX_INPUT_BYTES=262144
AMOUNTS=("sale_price","printing_cost","distribution_fee","shipping_cost","taxes","withholding","fixed_cost_per_copy","upfront_cost")
RATES=("platform_commission_rate","payment_fee_rate")
FIELDS=set(AMOUNTS+RATES+("schema_version","book_id","platform_id","channel_status","seller_funds_before_payout","currency","fx_to_xof"))
DATE_RE=re.compile(r"^\d{4}-\d{2}-\d{2}$")
CURRENCY_RE=re.compile(r"^[A-Z]{3}$")
CENT=Decimal("0.01")

class KidsProfitabilityError(ValueError):
    """Invalid or insufficiently evidenced profitability input."""

def _decimal(value: Any,label: str)->Decimal:
    if not isinstance(value,str) or len(value)>40: raise KidsProfitabilityError(f"{label}: chaîne décimale obligatoire.")
    try: number=Decimal(value)
    except InvalidOperation as exc: raise KidsProfitabilityError(f"{label}: nombre décimal invalide.") from exc
    if not number.is_finite() or number<0 or number>Decimal("1e18"): raise KidsProfitabilityError(f"{label}: valeur négative, non finie ou excessive.")
    return number

def _date(value: Any,label: str)->str:
    if not isinstance(value,str) or not DATE_RE.fullmatch(value): raise KidsProfitabilityError(f"{label}: date AAAA-MM-JJ obligatoire.")
    try: date.fromisoformat(value)
    except ValueError as exc: raise KidsProfitabilityError(f"{label}: date impossible.") from exc
    return value

def _evidenced(entry: Any,label: str,currency: str)->Decimal:
    if not isinstance(entry,dict) or set(entry)!={"value","currency","source","observed_at"}: raise KidsProfitabilityError(f"{label}: valeur, devise, source et date obligatoires.")
    if entry["currency"]!=currency: raise KidsProfitabilityError(f"{label}: devise différente de la devise source.")
    if not isinstance(entry["source"],str) or not entry["source"].strip() or len(entry["source"])>500: raise KidsProfitabilityError(f"{label}: référence de preuve obligatoire.")
    _date(entry["observed_at"],label)
    return _decimal(entry["value"],label)

def _unique_pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise KidsProfitabilityError(f"Clé JSON dupliquée : {key}")
        result[key]=value
    return result

def evaluate_offer(data: Any)->dict[str,Any]:
    if not isinstance(data,dict) or set(data)!=FIELDS: raise KidsProfitabilityError("Schéma incomplet/inattendu : aucun coût manquant ne peut être supposé nul.")
    if data["schema_version"]!=1: raise KidsProfitabilityError("schema_version non pris en charge.")
    for key in ("book_id","platform_id"):
        if not isinstance(data[key],str) or not data[key].strip() or len(data[key])>100: raise KidsProfitabilityError(f"{key} invalide.")
    if data["channel_status"] not in {"ELIGIBLE_ZERO_UPFRONT","HOLD","BLOCKED"}: raise KidsProfitabilityError("channel_status invalide.")
    if not isinstance(data["seller_funds_before_payout"],bool): raise KidsProfitabilityError("seller_funds_before_payout doit être booléen.")
    currency=data["currency"]
    if not isinstance(currency,str) or not CURRENCY_RE.fullmatch(currency): raise KidsProfitabilityError("Devise source ISO 4217 attendue.")
    values={k:_evidenced(data[k],k,currency) for k in AMOUNTS}
    rates={k:_evidenced(data[k],k,"RATE") for k in RATES}
    if any(x>1 for x in rates.values()): raise KidsProfitabilityError("Les taux doivent être compris entre 0 et 1.")
    fx=data["fx_to_xof"]
    if currency=="XOF":
        if fx is not None: raise KidsProfitabilityError("Pour XOF, fx_to_xof doit être null.")
        fx_rate,fx_source,fx_date=Decimal("1"),"XOF — conversion identité",None
    else:
        if not isinstance(fx,dict) or set(fx)!={"value","source","observed_at"}: raise KidsProfitabilityError("Conversion vers XOF et preuve datée obligatoires.")
        if not isinstance(fx["source"],str) or not fx["source"].strip(): raise KidsProfitabilityError("Source FX obligatoire.")
        fx_date=_date(fx["observed_at"],"FX")
        fx_rate=_decimal(fx["value"],"fx_to_xof")
        if fx_rate==0: raise KidsProfitabilityError("Le taux FX doit être strictement positif.")
        fx_source=fx["source"]
    with localcontext() as ctx:
        ctx.prec=40
        price=values["sale_price"]
        commission=price*rates["platform_commission_rate"]
        payment=price*rates["payment_fee_rate"]
        fixed=sum(values[k] for k in ("printing_cost","distribution_fee","shipping_cost","taxes","withholding","fixed_cost_per_copy"))
        net=price-commission-payment-fixed
        retained=Decimal("1")-rates["platform_commission_rate"]-rates["payment_fee_rate"]
        breakeven=(fixed/retained).quantize(CENT,rounding=ROUND_HALF_UP) if retained>0 else None
        def money(v): return str(v.quantize(CENT,rounding=ROUND_HALF_UP))
        gates={"channel_verified_zero_upfront":data["channel_status"]=="ELIGIBLE_ZERO_UPFRONT","no_initial_cost":values["upfront_cost"]==0,"seller_does_not_fund_order_before_payout":not data["seller_funds_before_payout"]}
        allowed=all(gates.values())
        return {"book_id":data["book_id"],"platform_id":data["platform_id"],"source_currency":currency,
            "sale_price":money(price),"platform_commission":money(commission),"payment_fee":money(payment),
            "fixed_and_per_copy_costs":money(fixed),"net_per_copy":money(net),
            "net_margin_rate":str((net/price).quantize(Decimal("0.0001"))) if price>0 else None,
            "break_even_sale_price":money(breakeven) if breakeven is not None else None,
            "xof":{"fx_rate_source_currency_to_xof":str(fx_rate),"fx_source":fx_source,"fx_observed_at":fx_date,
                "sale_price":money(price*fx_rate),"net_per_copy":money(net*fx_rate),
                "break_even_sale_price":money(breakeven*fx_rate) if breakeven is not None else None},
            "cashflow_gates":gates,"zero_upfront_policy_passed":values["upfront_cost"]==0 and not data["seller_funds_before_payout"],
            "channel_eligible_for_commercial_comparison":allowed,
            "commercial_decision":"PROFITABLE_ZERO_UPFRONT_CANDIDATE" if allowed and net>0 else "ZERO_UPFRONT_BUT_NOT_PROFITABLE" if allowed else "HOLD_OR_BLOCKED_NO_RECOMMENDATION",
            "publication_authorized":False,"all_inputs_have_dated_evidence":True,"market_prices_or_costs_invented":False,
            "note":"Résultat unitaire indicatif ; vérifier taxes, contrats, arrondis et versement réel. Aucun canal non certifié n'est recommandé."}

def load_offer(path: Path)->dict[str,Any]:
    try:
        if path.is_symlink() or path.stat().st_size>MAX_INPUT_BYTES: raise KidsProfitabilityError("Fichier symbolique ou trop volumineux.")
        data=json.loads(path.read_bytes().decode("utf-8",errors="strict"),object_pairs_hook=_unique_pairs)
    except KidsProfitabilityError: raise
    except (OSError,UnicodeError,json.JSONDecodeError) as exc: raise KidsProfitabilityError("Fichier absent, illisible ou JSON invalide.") from exc
    return data

def build_profitability_report(path: Path)->dict[str,Any]:
    return {"division_id":"papi_kids_publishing","calculation":evaluate_offer(load_offer(path)),"external_actions_performed":False,"publication_authorized":False}
