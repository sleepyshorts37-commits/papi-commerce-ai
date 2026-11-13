"""Unified read-only review orchestration for PAPI GLOBAL WORK."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from papi_core.global_work_evidence import EvidenceReviewError, review_source_evidence
from papi_core.global_work_ranking import GlobalWorkRankingError, rank_global_work_opportunities
from papi_core.global_work_source_registry import SourceRegistryError, validate_source_registry


class GlobalWorkReviewError(ValueError):
    """Invalid input for the unified opportunity review."""


def _normalized_claim(field: str, value: Any) -> str:
    if field == "eligible_countries" and isinstance(value, list):
        value = sorted(str(item).upper() for item in value)
    elif field == "payout_methods" and isinstance(value, list):
        value = sorted(str(item).strip().casefold() for item in value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def review_global_work_opportunities(
    candidates: list[dict[str, Any]],
    *,
    now: str | datetime,
    source_registry: dict[str, Any],
    evidence_records_by_source: dict[str, list[dict[str, Any]]] | None = None,
    applicant_country: str = "SN",
    max_evidence_age_days: int = 90,
) -> dict[str, Any]:
    """Validate registry, review supplied evidence, rank leads; never take action."""
    try:
        registry = validate_source_registry(source_registry)
    except (SourceRegistryError, ValueError) as exc:
        raise GlobalWorkReviewError("Registre des sources invalide.") from exc

    if evidence_records_by_source is None:
        evidence_records_by_source = {}
    if not isinstance(evidence_records_by_source, dict):
        raise GlobalWorkReviewError("evidence_records_by_source doit être un objet.")
    source_ids = {item["source_id"] for item in registry["sources"]}
    unknown_ids = sorted(set(evidence_records_by_source) - source_ids)
    if unknown_ids:
        raise GlobalWorkReviewError("Des preuves référencent des sources absentes du registre.")

    evidence_reviews: dict[str, dict[str, Any]] = {}
    for source in registry["sources"]:
        source_id = source["source_id"]
        records = evidence_records_by_source.get(source_id, [])
        try:
            review = review_source_evidence(
                records, now=now, max_age_days=max_evidence_age_days
            )
        except (EvidenceReviewError, ValueError) as exc:
            raise GlobalWorkReviewError(f"Preuves invalides pour la source {source_id}.") from exc

        contradictions = set(review["contradicted_fields"])
        fields = review["fields"]
        # Cross-check independently reviewed claims against registry declarations.
        for field, declared in (
            ("eligible_countries", source["eligible_countries"]),
            ("payout_methods", source["payout_methods"]),
        ):
            field_review = fields.get(field)
            if field_review and field_review["verdict"] == "supported":
                observed = [
                    item["value"] for item in review["evidence"] if item["field"] == field
                ][0]
                if _normalized_claim(field, declared) != _normalized_claim(field, observed):
                    contradictions.add(field)

        if contradictions:
            review["contradicted_fields"] = sorted(contradictions)
            review["overall_status"] = "contradiction_detected"
        evidence_reviews[source_id] = review

    try:
        ranked = rank_global_work_opportunities(
            candidates,
            now=now,
            applicant_country=applicant_country,
            source_registry=source_registry,
            evidence_reviews=evidence_reviews,
        )
    except (GlobalWorkRankingError, ValueError) as exc:
        raise GlobalWorkReviewError("Impossible de classer les opportunités fournies.") from exc

    counts = {
        "priority_for_human_review": sum(
            item["ranking_status"] == "priority_for_human_review" for item in ranked["results"]
        ),
        "hold_for_review": sum(
            item["ranking_status"] == "hold_for_review" for item in ranked["results"]
        ),
        "contradictory_sources": sum(
            item["overall_status"] == "contradiction_detected"
            for item in evidence_reviews.values()
        ),
        "sources_without_sufficient_evidence": sum(
            item["overall_status"] == "insufficient_evidence"
            for item in evidence_reviews.values()
        ),
    }
    return {
        **ranked,
        "source_registry_summary": {
            "source_count": registry["source_count"],
            "verified_count": registry["verified_count"],
            "enabled_count": registry["enabled_count"],
            "ingestion_enabled_count": registry["ingestion_enabled_count"],
        },
        "evidence_reviews": evidence_reviews,
        "review_summary": counts,
        "review_pipeline_version": "unified_read_only_v1",
        "human_approval_required": True,
        "qualified": False,
        "application_submitted": False,
        "external_actions_performed": False,
    }
