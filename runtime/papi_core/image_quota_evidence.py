"""Fail-closed quota evidence validation for PAPI image generation.

Evidence is an operator-reviewed attestation, not a live provider API query.
The provider's own transactional ledger remains authoritative at reservation time.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse


class QuotaEvidenceError(ValueError):
    """Missing, stale, mismatched or unsafe quota attestation."""


MAX_EVIDENCE_AGE = timedelta(hours=24)


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise QuotaEvidenceError(f"Horodatage {field} absent.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QuotaEvidenceError(f"Horodatage {field} invalide.") from exc
    if parsed.tzinfo is None:
        raise QuotaEvidenceError(f"Horodatage {field} sans fuseau horaire.")
    return parsed.astimezone(timezone.utc)


def validate_quota_evidence(
    evidence: dict[str, Any],
    *,
    provider: str,
    account_ref: str,
    model_id: str,
    estimated_units_per_image: int,
    required_images: int,
    now: datetime | None = None,
    provider_daily_limit: int | None = None,
    provider_model_cost: int | None = None,
) -> dict[str, Any]:
    """Validate reviewed evidence and exact provider configuration; no network call."""
    if not isinstance(evidence, dict):
        raise QuotaEvidenceError("Preuve de quota obligatoire ; aucune génération autorisée.")
    required = (
        "provider", "account_ref", "model_id", "source_url", "evidence_ref",
        "verified_at", "expires_at", "daily_quota_units", "spend_cap_minor",
    )
    if any(key not in evidence for key in required):
        raise QuotaEvidenceError("Attestation de quota incomplète.")
    if evidence["provider"] != provider or evidence["account_ref"] != account_ref:
        raise QuotaEvidenceError("L'attestation ne correspond pas au fournisseur/compte configuré.")
    if evidence["model_id"] != model_id:
        raise QuotaEvidenceError("L'attestation ne correspond pas au modèle demandé.")
    parsed_url = urlparse(evidence["source_url"]) if isinstance(evidence["source_url"], str) else None
    if parsed_url is None or parsed_url.scheme != "https" or not parsed_url.netloc:
        raise QuotaEvidenceError("Source officielle HTTPS obligatoire pour la preuve.")
    if not isinstance(evidence["evidence_ref"], str) or not evidence["evidence_ref"].strip():
        raise QuotaEvidenceError("Référence de preuve manquante.")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise QuotaEvidenceError("L'horloge doit inclure un fuseau horaire.")
    current = current.astimezone(timezone.utc)
    verified = _timestamp(evidence["verified_at"], "verified_at")
    expires = _timestamp(evidence["expires_at"], "expires_at")
    if verified > current or current - verified > MAX_EVIDENCE_AGE:
        raise QuotaEvidenceError("Preuve expirée par ancienneté : vérification de moins de 24 h requise.")
    if expires <= current or expires <= verified:
        raise QuotaEvidenceError("Preuve de quota expirée ou période incohérente.")
    daily = evidence["daily_quota_units"]
    if not isinstance(daily, int) or isinstance(daily, bool) or daily <= 0:
        raise QuotaEvidenceError("Quota journalier déclaré invalide.")
    if provider_daily_limit is not None and daily != provider_daily_limit:
        raise QuotaEvidenceError("Le quota déclaré ne correspond pas au plafond du ledger configuré.")
    if not isinstance(estimated_units_per_image, int) or isinstance(estimated_units_per_image, bool) or estimated_units_per_image <= 0:
        raise QuotaEvidenceError("Estimation par image invalide.")
    if provider_model_cost is not None and provider_model_cost != estimated_units_per_image:
        raise QuotaEvidenceError("Le coût modèle diffère entre l'attestation et le fournisseur.")
    if not isinstance(required_images, int) or isinstance(required_images, bool) or required_images < 1:
        raise QuotaEvidenceError("Nombre d'images demandé invalide.")
    estimated_total = estimated_units_per_image * required_images
    if estimated_total > daily:
        raise QuotaEvidenceError("Campagne supérieure au quota journalier déclaré.")
    if evidence["spend_cap_minor"] != 0:
        raise QuotaEvidenceError("Plafond monétaire non nul : cette campagne est interdite.")
    return {
        "provider": provider,
        "account_ref": account_ref,
        "model_id": model_id,
        "evidence_ref": evidence["evidence_ref"],
        "verified_at": verified.isoformat(),
        "expires_at": expires.isoformat(),
        "daily_quota_units": daily,
        "estimated_campaign_units": estimated_total,
        "spend_cap_minor": 0,
        "validation_mode": "operator_attestation_plus_provider_transactional_reservations",
        "live_provider_verification": False,
    }
