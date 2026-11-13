"""Evidence-based release maturity gates for PAPI WEB BUILDER.

A maturity level is awarded only when every cumulative criterion has a
verifiable, reviewed evidence record. This module does not deploy or publish.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

QUALITY_LEVELS = ("prototype", "mvp", "professional_production", "enterprise_critical")

LEVEL_REQUIREMENTS = {
    "prototype": (
        "static_generation",
        "html_safety",
        "responsive_smoke",
        "basic_accessibility",
        "automated_tests",
    ),
    "mvp": (
        "multi_page_navigation",
        "browser_matrix",
        "seo_basics",
        "export_integrity",
        "privacy_no_third_party",
    ),
    "professional_production": (
        "wcag_22_aa_audit",
        "independent_security_review",
        "field_core_web_vitals",
        "backup_restore_test",
        "monitoring_alerts",
        "privacy_legal_review",
        "owner_release_approval",
    ),
    "enterprise_critical": (
        "independent_penetration_test",
        "documented_threat_model",
        "disaster_recovery_exercise",
        "slo_error_budget",
        "periodic_access_review",
        "incident_response_exercise",
        "software_supply_chain_review",
        "signed_release_artifacts",
    ),
}


class QualityGateError(ValueError):
    """Raised when a requested maturity level lacks sufficient evidence."""


def _valid_evidence(record: Any) -> bool:
    if not isinstance(record, dict) or record.get("status") != "passed":
        return False
    evidence_ref = record.get("evidence_ref")
    reviewer = record.get("reviewer")
    verified_at = record.get("verified_at")
    if not all(isinstance(value, str) and value.strip() for value in (evidence_ref, reviewer, verified_at)):
        return False
    try:
        timestamp = datetime.fromisoformat(verified_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    return timestamp.tzinfo is not None and timestamp.utcoffset() is not None


def evaluate_quality_level(
    evidence: dict[str, Any],
    requested_level: str | None = None,
) -> dict[str, Any]:
    """Return the highest proven level and whether the requested level is allowed."""
    if not isinstance(evidence, dict):
        raise QualityGateError("Les preuves doivent être fournies sous forme d'objet.")
    if requested_level is not None and requested_level not in QUALITY_LEVELS:
        raise QualityGateError("Niveau de qualité inconnu.")

    achieved = None
    level_results = {}
    for level in QUALITY_LEVELS:
        required = LEVEL_REQUIREMENTS[level]
        missing = [key for key in required if not _valid_evidence(evidence.get(key))]
        level_results[level] = {"passed": not missing, "missing_evidence": missing}
        if not missing:
            achieved = level
        else:
            # Higher levels are cumulative; a missing lower-level proof blocks them.
            break

    if achieved is None:
        missing = level_results["prototype"]["missing_evidence"]
    else:
        achieved_index = QUALITY_LEVELS.index(achieved)
        missing = []
        if achieved_index < len(QUALITY_LEVELS) - 1:
            next_level = QUALITY_LEVELS[achieved_index + 1]
            missing = level_results.get(next_level, {}).get(
                "missing_evidence",
                list(LEVEL_REQUIREMENTS[next_level]),
            )

    allowed = requested_level is None or (
        achieved is not None and QUALITY_LEVELS.index(achieved) >= QUALITY_LEVELS.index(requested_level)
    )
    requested_missing = []
    if requested_level is not None and not allowed:
        for level in QUALITY_LEVELS[: QUALITY_LEVELS.index(requested_level) + 1]:
            requested_missing.extend(
                key for key in LEVEL_REQUIREMENTS[level]
                if not _valid_evidence(evidence.get(key))
            )

    return {
        "achieved_level": achieved,
        "requested_level": requested_level,
        "requested_level_allowed": allowed,
        "missing_for_next_level": missing,
        "missing_for_requested_level": list(dict.fromkeys(requested_missing)),
        "levels": level_results,
        "publication_authorized": False,
        "note": "Ce contrôle classe les preuves ; il n'autorise jamais à lui seul un déploiement ou une publication.",
    }


def require_quality_level(evidence: dict[str, Any], requested_level: str) -> dict[str, Any]:
    """Fail closed when the evidence bundle cannot support the requested level."""
    result = evaluate_quality_level(evidence, requested_level)
    if not result["requested_level_allowed"]:
        missing = ", ".join(result["missing_for_requested_level"])
        raise QualityGateError(
            f"Niveau '{requested_level}' refusé : preuves manquantes ou invalides ({missing})."
        )
    return result
