"""Governed registry for PAPI GLOBAL WORK opportunity sources.

This module validates metadata only. It does not fetch, crawl, authenticate or
assert that a platform accepts applicants from any particular country.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from papi_core.global_work_quality import GlobalWorkQualityError, canonicalize_url

SOURCE_TYPES = {"job_board", "freelance_marketplace", "microtask_platform", "company_careers", "grant_program", "other"}
ACCESS_MODES = {"manual", "authorized_api", "authorized_feed"}
VERIFICATION_STATES = {"unverified", "verified", "suspended"}
COUNTRY_CODE = re.compile(r"^[A-Z]{2}$")


class SourceRegistryError(ValueError):
    """Invalid source registry metadata."""


def _date(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise SourceRegistryError(f"{field} doit être une date ISO-8601.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceRegistryError(f"{field} doit être une date ISO-8601.") from exc
    if parsed.tzinfo is None:
        raise SourceRegistryError(f"{field} doit inclure un fuseau horaire.")


def validate_source_record(source: dict[str, Any]) -> dict[str, Any]:
    """Validate one source record and return a safe, non-activating summary."""
    if not isinstance(source, dict):
        raise SourceRegistryError("Une source doit être un objet.")
    required_text = ("source_id", "name", "source_type", "url", "access_mode", "verification_status")
    for key in required_text:
        if not isinstance(source.get(key), str) or not source[key].strip():
            raise SourceRegistryError(f"{key} est obligatoire.")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,63}", source["source_id"]):
        raise SourceRegistryError("source_id invalide.")
    if source["source_type"] not in SOURCE_TYPES:
        raise SourceRegistryError("source_type non pris en charge.")
    if source["access_mode"] not in ACCESS_MODES:
        raise SourceRegistryError("access_mode non pris en charge.")
    if source["verification_status"] not in VERIFICATION_STATES:
        raise SourceRegistryError("verification_status non pris en charge.")
    try:
        url = canonicalize_url(source["url"])
    except GlobalWorkQualityError as exc:
        raise SourceRegistryError("URL de source publique HTTPS invalide.") from exc

    countries = source.get("eligible_countries", [])
    if not isinstance(countries, list) or any(
        not isinstance(code, str) or not COUNTRY_CODE.fullmatch(code.upper()) for code in countries
    ):
        raise SourceRegistryError("eligible_countries doit contenir des codes ISO alpha-2.")
    methods = source.get("payout_methods", [])
    if not isinstance(methods, list) or any(not isinstance(item, str) or not item.strip() for item in methods):
        raise SourceRegistryError("payout_methods doit être une liste de textes.")
    evidence = source.get("verification_evidence")
    verified = source["verification_status"] == "verified"
    if verified:
        if not isinstance(evidence, dict):
            raise SourceRegistryError("Une source vérifiée exige une preuve structurée.")
        for key in ("country_eligibility_url", "payout_terms_url", "terms_url"):
            try:
                canonicalize_url(evidence.get(key, ""))
            except GlobalWorkQualityError as exc:
                raise SourceRegistryError(f"Preuve publique HTTPS requise : {key}.") from exc
        _date(source.get("verified_at"), "verified_at")
        if not isinstance(source.get("verified_by"), str) or not source["verified_by"].strip():
            raise SourceRegistryError("verified_by est obligatoire pour une source vérifiée.")
    elif source.get("verified_at") is not None:
        _date(source["verified_at"], "verified_at")

    enabled_requested = source.get("enabled", False)
    if not isinstance(enabled_requested, bool):
        raise SourceRegistryError("enabled doit être booléen.")
    operational = verified and source["verification_status"] == "verified" and enabled_requested
    return {
        "source_id": source["source_id"],
        "name": source["name"].strip(),
        "url": url,
        "verification_status": source["verification_status"],
        "eligible_countries": [code.upper() for code in countries],
        "payout_methods": list(methods),
        "enabled": operational,
        "ingestion_allowed": operational and source["access_mode"] in {"authorized_api", "authorized_feed"},
        "human_review_required": True,
    }


def validate_source_registry(registry: dict[str, Any]) -> dict[str, Any]:
    """Validate registry uniqueness and summarize activation eligibility."""
    if not isinstance(registry, dict) or not isinstance(registry.get("sources"), list):
        raise SourceRegistryError("Le registre doit contenir une liste sources.")
    validated = []
    seen = set()
    for source in registry["sources"]:
        item = validate_source_record(source)
        if item["source_id"] in seen:
            raise SourceRegistryError("source_id dupliqué.")
        seen.add(item["source_id"])
        validated.append(item)
    return {
        "sources": validated,
        "source_count": len(validated),
        "verified_count": sum(item["verification_status"] == "verified" for item in validated),
        "enabled_count": sum(item["enabled"] for item in validated),
        "ingestion_enabled_count": sum(item["ingestion_allowed"] for item in validated),
        "external_actions_performed": False,
    }
