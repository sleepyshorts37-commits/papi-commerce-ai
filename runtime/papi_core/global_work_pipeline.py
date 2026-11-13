"""Deterministic read-only qualification pipeline for PAPI GLOBAL WORK."""
from __future__ import annotations
from datetime import datetime
from typing import Any
from papi_core.global_work_quality import (
    assess_candidate_quality, deduplicate_candidates, evaluate_candidate_freshness,
)
from papi_core.global_work_eligibility import evaluate_work_opportunity

def qualify_work_candidates(
    candidates: list[dict[str, Any]], *, now: str | datetime,
    applicant_country: str = "SN", max_age_days: int = 30,
) -> dict[str, Any]:
    """Deduplicate, assess freshness/completeness and evaluate supplied economics.

    This pipeline never approves, applies, contacts a source, or makes a payment.
    """
    if not isinstance(candidates, list):
        raise ValueError("Une liste de candidats est requise.")
    dedup = deduplicate_candidates(candidates)
    results = []
    for candidate in dedup["unique_candidates"]:
        quality = assess_candidate_quality(candidate)
        freshness = evaluate_candidate_freshness(candidate, now=now, max_age_days=max_age_days)
        economics_input = candidate.get("eligibility")
        if isinstance(economics_input, dict):
            economics = evaluate_work_opportunity(economics_input, applicant_country=applicant_country)
        else:
            economics = {
                "status": "insufficient_evidence",
                "missing_fields": ["eligibility"],
                "blockers": [],
                "qualified": False,
                "human_approval_required": True,
                "application_submitted": False,
                "payment_made": False,
            }
        ready = (
            quality["quality"] == "needs_human_review"
            and freshness["freshness"] == "fresh"
            and economics["status"] == "ready_for_human_review"
        )
        results.append({
            "candidate_id": candidate.get("candidate_id"),
            "source_id": candidate.get("source_id"),
            "title": candidate.get("title"),
            "source_url": candidate.get("source_url"),
            "quality": quality,
            "freshness": freshness,
            "economics": economics,
            "pipeline_status": "ready_for_human_review" if ready else "hold_for_review",
            "qualified": False,
            "application_submitted": False,
        })
    return {
        "input_count": len(candidates),
        "unique_count": dedup["unique_count"],
        "duplicate_count": dedup["duplicate_count"],
        "duplicates": dedup["duplicates"],
        "results": results,
        "human_approval_required": True,
        "external_actions_performed": False,
    }
