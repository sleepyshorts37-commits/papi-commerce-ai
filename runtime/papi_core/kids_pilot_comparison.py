"""Compare the five PAPI KIDS pilot concepts using validated niche evidence."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .kids_niche_research import KidsNicheError, assess_niche

MAX_BYTES=2*1024*1024
PILOTS={
 "PKP-0001":"Nia et la rivière aux mille reflets",
 "PKP-0002":"Le marché des nombres de Sami",
 "PKP-0003":"Le petit atlas de mes émotions",
 "PKP-0004":"Les missions futées de la savane",
 "PKP-0005":"Jardins de formes : mon grand coloriage",
}
class KidsPilotComparisonError(ValueError):
    """Invalid pilot portfolio comparison input."""

def _pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise KidsPilotComparisonError(f"Clé JSON dupliquée : {key}")
        result[key]=value
    return result

def compare_pilots(data: Any)->dict[str,Any]:
    if not isinstance(data,dict) or set(data)!={"schema_version","observed_at","pilots"}:
        raise KidsPilotComparisonError("Le portefeuille doit contenir schema_version, observed_at et pilots.")
    if data["schema_version"]!=1: raise KidsPilotComparisonError("schema_version non pris en charge.")
    if not isinstance(data["observed_at"],str) or len(data["observed_at"])!=10:
        raise KidsPilotComparisonError("Date de comparaison AAAA-MM-JJ obligatoire.")
    from datetime import date
    try: date.fromisoformat(data["observed_at"])
    except ValueError as exc: raise KidsPilotComparisonError("Date de comparaison impossible.") from exc
    pilots=data["pilots"]
    if not isinstance(pilots,list) or len(pilots)!=5:
        raise KidsPilotComparisonError("Fournir exactement les cinq concepts pilotes PAPI KIDS.")
    seen=set(); keywords=set(); rows=[]
    for entry in pilots:
        if not isinstance(entry,dict) or set(entry)!={"book_id","concept_title","niche_evidence"}:
            raise KidsPilotComparisonError("Chaque pilote exige book_id, concept_title et niche_evidence.")
        book_id=entry["book_id"]
        if book_id not in PILOTS or book_id in seen:
            raise KidsPilotComparisonError(f"Identifiant pilote inconnu ou dupliqué : {book_id}")
        seen.add(book_id)
        if entry["concept_title"]!=PILOTS[book_id]:
            raise KidsPilotComparisonError(f"Titre inattendu pour {book_id}.")
        try: result=assess_niche(entry["niche_evidence"])
        except KidsNicheError as exc: raise KidsPilotComparisonError(f"{book_id}: {exc}") from exc
        key=(result["marketplace"],result["country"],result["language"],result["keyword"].casefold())
        if key in keywords: raise KidsPilotComparisonError("Chaque concept doit être évalué avec une niche/mot-clé distinct dans le même marché et la même langue.")
        keywords.add(key)
        rows.append({"book_id":book_id,"concept_title":entry["concept_title"],
            "keyword":result["keyword"],"marketplace":result["marketplace"],
            "country":result["country"],"language":result["language"],
            "evidence_observed_at":result["observed_at"],"search_results_count":result["search_results_count"],
            "top_three_bsr":result["top_three_bsr"],
            "first_page_average_reviews":result["first_page_average_reviews"],
            "signals_passed":result["signals_passed"],"criteria":result["criteria"],
            "screening_result":result["screening_result"],
            "decision":"HUMAN_REVIEW_REQUIRED"})
    if seen!=set(PILOTS): raise KidsPilotComparisonError("Un ou plusieurs concepts pilotes sont absents.")
    # Score transparent: one point per passed heuristic, no hidden weighting.
    rows.sort(key=lambda r:(-r["signals_passed"],r["book_id"]))
    for rank,row in enumerate(rows,1):
        row["rank_by_screening_signals"]=rank
        row["screening_score_out_of_3"]=row["signals_passed"]
    return {"division_id":"papi_kids_publishing","comparison_date":data["observed_at"],
        "pilot_count":5,"ranking_method":"Nombre de trois heuristiques satisfaites (0–3), puis identifiant pour départager les égalités. Aucun poids commercial caché.",
        "ranked_pilots":rows,
        "portfolio_status":"EVIDENCE_COMPLETE_FOR_FIVE_PILOTS",
        "interpretation":"Ce classement priorise les recherches à approfondir ; il ne prédit ni ventes, ni bénéfices, ni succès éditorial.",
        "next_review":"Contrôler différenciation, qualité des livres concurrents, formats, prix, sous-catégories et évolution des BSR avant décision humaine.",
        "automatic_go_authorized":False,"publication_authorized":False,
        "market_data_invented":False,"external_actions_performed":False}

def load_comparison(path: Path)->dict[str,Any]:
    try:
        if path.is_symlink() or path.stat().st_size>MAX_BYTES: raise KidsPilotComparisonError("Fichier symbolique ou trop volumineux.")
        return json.loads(path.read_bytes().decode("utf-8",errors="strict"),object_pairs_hook=_pairs)
    except KidsPilotComparisonError: raise
    except (OSError,UnicodeError,json.JSONDecodeError) as exc: raise KidsPilotComparisonError("Fichier absent, illisible ou JSON invalide.") from exc

def build_pilot_comparison_report(path: Path)->dict[str,Any]:
    return {"comparison":compare_pilots(load_comparison(path)),
        "external_actions_performed":False,"automatic_go_authorized":False}
