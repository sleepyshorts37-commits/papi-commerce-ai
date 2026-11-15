"""Evidence-backed Amazon KDP niche screening; never auto-approves a book."""
from __future__ import annotations
import json,re
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Any

MAX_BYTES=512*1024
DATE_RE=re.compile(r"^\d{4}-\d{2}-\d{2}$")
ROOT=Path(__file__).resolve().parents[2]

class KidsNicheError(ValueError):
    """Invalid or insufficient Amazon niche evidence."""

def _date(value: Any,label: str)->str:
    if not isinstance(value,str) or not DATE_RE.fullmatch(value):
        raise KidsNicheError(f"{label}: date AAAA-MM-JJ obligatoire.")
    try: date.fromisoformat(value)
    except ValueError as exc: raise KidsNicheError(f"{label}: date impossible.") from exc
    return value

def _nonnegative_int(value: Any,label: str)->int:
    if isinstance(value,bool) or not isinstance(value,int) or value<0 or value>2_147_483_647:
        raise KidsNicheError(f"{label}: entier positif ou nul obligatoire.")
    return value

def _unique_pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise KidsNicheError(f"Clé JSON dupliquée : {key}")
        result[key]=value
    return result

def validate_assessment(data: Any)->list[str]:
    errors=[]
    required={"schema_version","marketplace","country","keyword","language","observed_at","search_results_count","search_source","search_url","products"}
    if not isinstance(data,dict) or set(data)!=required:
        return ["Schéma de recherche incomplet ou inattendu."]
    if data["schema_version"]!=1: errors.append("schema_version non pris en charge.")
    for key in ("marketplace","country","keyword","language","search_source","search_url"):
        value=data[key]
        if not isinstance(value,str) or not value.strip() or len(value)>1000: errors.append(f"{key} invalide.")
    try: _date(data["observed_at"],"observed_at")
    except KidsNicheError as exc: errors.append(str(exc))
    try: _nonnegative_int(data["search_results_count"],"search_results_count")
    except KidsNicheError as exc: errors.append(str(exc))
    products=data["products"]
    if not isinstance(products,list) or not 10<=len(products)<=20:
        errors.append("Fournir entre 10 et 20 livres concurrents de la première page.")
        return errors
    seen=set()
    product_fields={"rank","title","asin","bsr","reviews","price","format","source_url","observed_at"}
    for index,item in enumerate(products):
        label=f"products[{index}]"
        if not isinstance(item,dict) or set(item)!=product_fields:
            errors.append(f"{label}: champs incomplets ou inattendus."); continue
        for key in ("title","asin","format","source_url"):
            if not isinstance(item[key],str) or not item[key].strip() or len(item[key])>1000:
                errors.append(f"{label}.{key} invalide.")
        asin=item.get("asin")
        if isinstance(asin,str):
            if asin in seen: errors.append(f"ASIN dupliqué : {asin}")
            seen.add(asin)
        for key in ("rank","bsr","reviews"):
            try:
                val=_nonnegative_int(item[key],f"{label}.{key}")
                if key=="rank" and val==0: raise KidsNicheError(f"{label}.rank doit commencer à 1.")
                if key=="bsr" and val==0: raise KidsNicheError(f"{label}.bsr doit être strictement positif.")
            except KidsNicheError as exc: errors.append(str(exc))
        if item.get("price") is not None and (not isinstance(item["price"],str) or len(item["price"])>80):
            errors.append(f"{label}.price doit être une chaîne ou null.")
        try: _date(item["observed_at"],f"{label}.observed_at")
        except KidsNicheError as exc: errors.append(str(exc))
    ranks=[p.get("rank") for p in products if isinstance(p,dict) and isinstance(p.get("rank"),int) and not isinstance(p.get("rank"),bool)]
    if len(ranks)==len(products) and sorted(ranks)!=list(range(1,len(products)+1)):
        errors.append("Les rangs doivent être uniques et continus de 1 à N.")
    return errors

def assess_niche(data: Any)->dict[str,Any]:
    errors=validate_assessment(data)
    if errors: raise KidsNicheError(" | ".join(errors))
    products=sorted(data["products"],key=lambda p:p["rank"])
    top_three=products[:3]
    result_count=data["search_results_count"]
    average_reviews=mean(p["reviews"] for p in products)
    checks={
        "competition_below_2500_results":result_count<2500,
        "top_three_bsr_below_100000":all(p["bsr"]<100000 for p in top_three),
        "first_page_average_reviews_below_50":average_reviews<50,
    }
    passed=sum(checks.values())
    if passed==3: screening="PROMISING_FOR_HUMAN_REVIEW"
    elif passed==2: screening="REWORK_AND_RESEARCH_MORE"
    else: screening="WEAK_SIGNAL_STOP_OR_REPOSITION"
    return {
        "marketplace":data["marketplace"],"country":data["country"],"keyword":data["keyword"],
        "language":data["language"],"observed_at":data["observed_at"],
        "sample_size":len(products),"search_results_count":result_count,
        "top_three_bsr":[{"rank":p["rank"],"asin":p["asin"],"bsr":p["bsr"]} for p in top_three],
        "first_page_average_reviews":round(average_reviews,2),
        "criteria":checks,"signals_passed":passed,"screening_result":screening,
        "decision":"HUMAN_REVIEW_REQUIRED",
        "limitations":[
            "Le nombre de résultats Amazon est approximatif, dépend de la requête, du pays, de la langue et de la personnalisation.",
            "Le BSR est un indicateur relatif et variable ; il ne fournit pas le nombre exact de ventes quotidiennes.",
            "Les avis sont un indicateur de maturité/concurrence, pas une preuve directe de ventes ni de facilité de positionnement.",
            "Un échantillon de 10 à 20 résultats ne représente pas toute la niche ; contrôler les sous-catégories, formats, prix, qualité et tendances.",
            "Ces seuils sont des heuristiques issues du protocole interne inspiré de la capture, pas des garanties Amazon ni des seuils universels."
        ],
        "evidence":{"search_source":data["search_source"],"search_url":data["search_url"],
            "product_sources":[{"rank":p["rank"],"asin":p["asin"],"url":p["source_url"],"observed_at":p["observed_at"]} for p in products]},
        "market_data_invented":False,"automatic_go_authorized":False,
        "publication_authorized":False
    }

def load_assessment(path: Path)->dict[str,Any]:
    try:
        if path.is_symlink() or path.stat().st_size>MAX_BYTES: raise KidsNicheError("Fichier symbolique ou trop volumineux.")
        return json.loads(path.read_bytes().decode("utf-8",errors="strict"),object_pairs_hook=_unique_pairs)
    except KidsNicheError: raise
    except (OSError,UnicodeError,json.JSONDecodeError) as exc: raise KidsNicheError("Fichier absent, illisible ou JSON invalide.") from exc

def build_niche_report(path: Path)->dict[str,Any]:
    return {"division_id":"papi_kids_publishing","niche_assessment":assess_niche(load_assessment(path)),
            "external_actions_performed":False,"automatic_go_authorized":False}
