"""Explainable, conservative ranking for PAPI GLOBAL WORK opportunities."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from papi_core.global_work_pipeline import qualify_work_candidates
from papi_core.global_work_source_registry import validate_source_registry


class GlobalWorkRankingError(ValueError):
    """Invalid ranking input."""


def _positive(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return False
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return False
    return number.is_finite() and number > 0


def rank_global_work_opportunities(
    candidates: list[dict[str, Any]],
    *,
    now: str | datetime,
    applicant_country: str = "SN",
    source_registry: dict[str, Any] | None = None,
    evidence_reviews: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Rank supplied leads for human review; ranking is never approval or qualification.

    Scores are rule-based priority indicators, not probabilities or guarantees.
    Unknown facts receive no positive credit. No network or external action occurs.
    """
    if not isinstance(candidates, list):
        raise GlobalWorkRankingError("Une liste de candidats est requise.")
    if evidence_reviews is not None and not isinstance(evidence_reviews, dict):
        raise GlobalWorkRankingError("evidence_reviews doit être un objet indexé par source_id.")

    sources: dict[str, dict[str, Any]] = {}
    if source_registry is not None:
        try:
            validated = validate_source_registry(source_registry)
        except ValueError as exc:
            raise GlobalWorkRankingError("Registre de sources invalide.") from exc
        sources = {item["source_id"]: item for item in validated["sources"]}

    pipeline = qualify_work_candidates(
        candidates, now=now, applicant_country=applicant_country
    )
    ranked = []
    for result in pipeline["results"]:
        score = 0
        reasons: list[str] = []
        blockers: list[str] = []
        source_id = result.get("source_id")
        source = sources.get(source_id) if isinstance(source_id, str) else None
        evidence = (evidence_reviews or {}).get(source_id, {}) if isinstance(source_id, str) else {}

        freshness = result["freshness"]["freshness"]
        if freshness == "fresh":
            score += 20
            reasons.append("publication_fraiche:+20")
        elif freshness == "stale":
            score -= 15
            reasons.append("publication_perimee:-15")
        elif freshness == "future_date":
            blockers.append("date_publication_dans_le_futur")
        else:
            score -= 5
            reasons.append("date_publication_inconnue:-5")

        if result["quality"]["quality"] == "needs_human_review":
            score += 15
            reasons.append("donnees_de_base_completes:+15")
        else:
            score -= 10
            reasons.append("donnees_incompletes:-10")

        economics = result["economics"]
        if economics.get("country_status") == "listed":
            score += 15
            reasons.append("pays_demandeur_liste:+15")
        elif economics.get("country_status") == "not_listed":
            blockers.append("pays_demandeur_non_admissible")
        else:
            score -= 10
            reasons.append("admissibilite_pays_inconnue:-10")

        if economics.get("status") == "ready_for_human_review":
            score += 20
            reasons.append("donnees_economiques_et_pieces_completes:+20")
        else:
            score -= 10
            reasons.append("verification_economique_incomplete:-10")
        if _positive(economics.get("estimated_net")):
            score += 10
            reasons.append("revenu_net_estime_positif:+10")
        elif economics.get("estimated_net") is not None:
            blockers.append("revenu_net_non_positif")
        else:
            reasons.append("revenu_net_inconnu:aucun_bonus")
        if _positive(economics.get("estimated_hourly_net")):
            score += 10
            reasons.append("revenu_horaire_net_positif:+10")

        if source is None:
            score -= 10
            reasons.append("source_non_repertoriee_ou_non_validee:-10")
            blockers.append("source_non_repertoriee")
        else:
            if source["verification_status"] == "suspended":
                blockers.append("source_suspendue")
            elif source["verification_status"] == "verified" and source["enabled"]:
                score += 15
                reasons.append("source_verifiee_et_active:+15")
            else:
                score -= 10
                reasons.append("source_non_active_ou_non_verifiee:-10")
                blockers.append("source_non_verifiee_ou_inactive")
            if source["verification_status"] == "verified" and not source["enabled"]:
                blockers.append("source_verifiee_mais_desactivee")

        evidence_status = evidence.get("overall_status") if isinstance(evidence, dict) else None
        if evidence_status == "contradiction_detected":
            blockers.append("preuves_contradictoires")
        elif evidence_status == "human_review_required":
            score += 5
            reasons.append("preuves_coherentes_a_revoir_humainement:+5")
        else:
            score -= 5
            reasons.append("preuves_absentes_ou_insuffisantes:-5")
            blockers.append("preuves_insuffisantes")

        score = max(0, min(100, score))
        review_priority = not blockers and score >= 50
        ranked.append({
            **result,
            "priority_score": score,
            "ranking_status": "priority_for_human_review" if review_priority else "hold_for_review",
            "ranking_reasons": reasons,
            "ranking_blockers": sorted(set(blockers)),
            "qualified": False,
            "human_approval_required": True,
            "application_submitted": False,
        })

    ranked.sort(key=lambda item: (-item["priority_score"], str(item.get("candidate_id") or ""),
                                  str(item.get("source_url") or "")))
    for position, item in enumerate(ranked, start=1):
        item["rank"] = position
    return {
        "results": ranked,
        "input_count": pipeline["input_count"],
        "unique_count": pipeline["unique_count"],
        "duplicate_count": pipeline["duplicate_count"],
        "duplicates": pipeline["duplicates"],
        "ranking_method": "deterministic_rules_v1",
        "human_approval_required": True,
        "qualified": False,
        "application_submitted": False,
        "external_actions_performed": False,
    }
