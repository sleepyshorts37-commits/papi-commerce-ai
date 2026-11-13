"""Safe intake and triage of platform candidates discovered by PAPI AI WORKERS.

This module processes search-result metadata supplied by an authorized search
adapter. It does not perform web searches, fetch pages, register accounts or
claim that a platform is eligible for Senegal-based operators.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from papi_core.global_work_quality import GlobalWorkQualityError, canonicalize_url

POLICY_STATES = {"allowed", "conditional", "prohibited", "unknown"}
COUNTRY_STATES = {"eligible", "ineligible", "unknown"}
PAYOUT_STATES = {"supported", "unsupported", "unknown"}
CANDIDATE_STATES = {"candidate", "needs_human_review", "human_registration_required", "rejected"}
_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")


class PlatformDiscoveryError(ValueError):
    """Invalid platform discovery input."""


def _timestamp(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise PlatformDiscoveryError(f"{field} doit être une date ISO-8601.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PlatformDiscoveryError(f"{field} doit être une date ISO-8601.") from exc
    if parsed.tzinfo is None:
        raise PlatformDiscoveryError(f"{field} doit inclure un fuseau horaire.")


def review_platform_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Validate one discovered candidate and return conservative next steps.

    All claims remain unverified until independently reviewed by a human.
    """
    if not isinstance(candidate, dict):
        raise PlatformDiscoveryError("Une plateforme candidate doit être un objet.")
    for field in ("platform_id", "name", "url", "discovery_query", "discovered_at", "discovered_by"):
        if not isinstance(candidate.get(field), str) or not candidate[field].strip():
            raise PlatformDiscoveryError(f"{field} est obligatoire.")
    if not _ID.fullmatch(candidate["platform_id"]):
        raise PlatformDiscoveryError("platform_id invalide.")
    try:
        url = canonicalize_url(candidate["url"])
    except GlobalWorkQualityError as exc:
        raise PlatformDiscoveryError("URL officielle publique HTTPS invalide.") from exc
    _timestamp(candidate["discovered_at"], "discovered_at")

    policy = candidate.get("ai_agent_policy", "unknown")
    country = candidate.get("senegal_eligibility", "unknown")
    payout = candidate.get("senegal_payout_status", "unknown")
    if policy not in POLICY_STATES:
        raise PlatformDiscoveryError("ai_agent_policy invalide.")
    if country not in COUNTRY_STATES:
        raise PlatformDiscoveryError("senegal_eligibility invalide.")
    if payout not in PAYOUT_STATES:
        raise PlatformDiscoveryError("senegal_payout_status invalide.")

    evidence_urls = candidate.get("evidence_urls", [])
    if not isinstance(evidence_urls, list):
        raise PlatformDiscoveryError("evidence_urls doit être une liste.")
    safe_evidence = []
    for item in evidence_urls:
        if not isinstance(item, str):
            raise PlatformDiscoveryError("Chaque preuve doit être une URL HTTPS.")
        try:
            safe_evidence.append(canonicalize_url(item))
        except GlobalWorkQualityError as exc:
            raise PlatformDiscoveryError("URL de preuve publique HTTPS invalide.") from exc

    blockers = []
    if policy == "prohibited":
        blockers.append("ai_agents_prohibited")
    elif policy in {"conditional", "unknown"}:
        blockers.append("ai_agent_policy_requires_review")
    if country == "ineligible":
        blockers.append("senegal_ineligible")
    elif country == "unknown":
        blockers.append("senegal_eligibility_unverified")
    if payout == "unsupported":
        blockers.append("senegal_payout_unavailable")
    elif payout == "unknown":
        blockers.append("senegal_payout_unverified")
    if not safe_evidence:
        blockers.append("official_evidence_missing")

    registration = candidate.get("registration_required", False)
    if not isinstance(registration, bool):
        raise PlatformDiscoveryError("registration_required doit être booléen.")
    if registration:
        blockers.append("user_registration_required")

    if policy == "prohibited" or country == "ineligible" or payout == "unsupported":
        status = "rejected"
    elif registration:
        status = "human_registration_required"
    elif blockers:
        status = "needs_human_review"
    else:
        status = "candidate"

    return {
        "platform_id": candidate["platform_id"],
        "name": candidate["name"].strip(),
        "url": url,
        "discovery_query": candidate["discovery_query"].strip(),
        "discovered_at": candidate["discovered_at"],
        "discovered_by": candidate["discovered_by"].strip(),
        "ai_agent_policy": policy,
        "senegal_eligibility": country,
        "senegal_payout_status": payout,
        "evidence_urls": safe_evidence,
        "status": status,
        "blockers": blockers,
        "requires_user_registration": registration,
        "human_review_required": True,
        "verified": False,
        "account_created": False,
        "external_actions_performed": False,
    }


def review_platform_candidates(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Review a batch, reject duplicate IDs, and summarize human follow-up."""
    if not isinstance(candidates, list):
        raise PlatformDiscoveryError("candidates doit être une liste.")
    results = []
    seen = set()
    for candidate in candidates:
        result = review_platform_candidate(candidate)
        if result["platform_id"] in seen:
            raise PlatformDiscoveryError("platform_id dupliqué dans le lot.")
        seen.add(result["platform_id"])
        results.append(result)
    return {
        "results": results,
        "candidate_count": len(results),
        "human_review_count": sum(item["human_review_required"] for item in results),
        "registration_required_count": sum(item["requires_user_registration"] for item in results),
        "rejected_count": sum(item["status"] == "rejected" for item in results),
        "verified_count": 0,
        "external_actions_performed": False,
    }
