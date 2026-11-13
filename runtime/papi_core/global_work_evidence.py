"""Evidence and contradiction checks for GLOBAL WORK source verification.

Evidence is supplied by an authorized human/review process. This module does
not visit URLs, fetch pages, or establish that a claim is true.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from papi_core.global_work_quality import GlobalWorkQualityError, canonicalize_url

ALLOWED_FIELDS = {"eligible_countries", "payout_methods", "fees", "ai_policy", "terms"}
ALLOWED_VERDICTS = {"supported", "contradicted", "unknown"}


class EvidenceReviewError(ValueError):
    """Invalid evidence review input."""


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceReviewError(f"{field} doit être une date ISO-8601.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceReviewError(f"{field} doit être une date ISO-8601.") from exc
    if parsed.tzinfo is None:
        raise EvidenceReviewError(f"{field} doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)


def review_source_evidence(
    evidence_records: list[dict[str, Any]], *, now: str,
    max_age_days: int = 90,
) -> dict[str, Any]:
    """Assess supplied evidence metadata and claims; never browse or auto-verify."""
    current = _timestamp(now, "now")
    if not isinstance(max_age_days, int) or isinstance(max_age_days, bool) or max_age_days < 0:
        raise EvidenceReviewError("max_age_days doit être un entier positif ou nul.")
    if not isinstance(evidence_records, list):
        raise EvidenceReviewError("evidence_records doit être une liste.")

    reviewed = []
    by_field: dict[str, list[dict[str, Any]]] = {}
    for index, record in enumerate(evidence_records):
        if not isinstance(record, dict):
            raise EvidenceReviewError(f"Preuve {index}: objet requis.")
        field = record.get("field")
        if field not in ALLOWED_FIELDS:
            raise EvidenceReviewError(f"Preuve {index}: champ non pris en charge.")
        url = record.get("url")
        try:
            normalized_url = canonicalize_url(url)
        except GlobalWorkQualityError as exc:
            raise EvidenceReviewError(f"Preuve {index}: URL HTTPS publique requise.") from exc
        observed_at = _timestamp(record.get("observed_at"), f"evidence[{index}].observed_at")
        if observed_at > current:
            freshness = "future_dated"
        elif (current - observed_at).total_seconds() > max_age_days * 86400:
            freshness = "stale"
        else:
            freshness = "recent"
        value = record.get("value")
        if value is None or value == "" or value == []:
            raise EvidenceReviewError(f"Preuve {index}: valeur observée obligatoire.")
        reviewer = record.get("reviewer")
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise EvidenceReviewError(f"Preuve {index}: reviewer humain obligatoire.")
        item = {
            "field": field, "url": normalized_url, "value": value,
            "observed_at": observed_at.isoformat(), "freshness": freshness,
            "reviewer": reviewer.strip(),
        }
        reviewed.append(item)
        by_field.setdefault(field, []).append(item)

    field_results = {}
    for field, entries in by_field.items():
        values = {repr(entry["value"]) for entry in entries}
        has_stale = any(entry["freshness"] != "recent" for entry in entries)
        if len(values) > 1:
            verdict = "contradicted"
        elif has_stale:
            verdict = "unknown"
        else:
            verdict = "supported"
        field_results[field] = {
            "verdict": verdict,
            "evidence_count": len(entries),
            "distinct_observations": len(values),
            "requires_human_review": True,
        }

    contradictions = sorted(field for field, result in field_results.items()
                            if result["verdict"] == "contradicted")
    unresolved = sorted(field for field, result in field_results.items()
                        if result["verdict"] == "unknown")
    return {
        "fields": field_results,
        "evidence": reviewed,
        "contradicted_fields": contradictions,
        "unresolved_fields": unresolved,
        "overall_status": "contradiction_detected" if contradictions
            else ("insufficient_evidence" if unresolved or not reviewed else "human_review_required"),
        "verified": False,
        "external_actions_performed": False,
    }
