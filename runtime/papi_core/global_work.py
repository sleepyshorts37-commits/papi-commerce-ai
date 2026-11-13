"""Évaluation locale d'opportunités de missions internationales.

Aucun scraping, candidature, contact externe, paiement ou appel réseau n'est effectué.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

ALLOWED_AUTOMATION_POLICIES = {"allowed", "human_submission_only", "prohibited", "unknown"}
ALLOWED_AI_POLICIES = {"allowed", "restricted", "prohibited", "unknown"}
REQUIRED_FIELDS = {
    "id", "source_url", "title", "description", "country_eligibility",
    "eligible_countries", "compensation_amount", "currency", "estimated_minutes",
    "upfront_cost", "automation_policy", "ai_policy", "human_presence_required",
    "payout_methods",
}
SENSITIVE_KEYS = {
    "password", "token", "access_token", "secret", "otp", "pin", "cvv",
    "card_number", "bank_account", "private_key",
}


class GlobalWorkError(ValueError):
    """Données d'opportunité internationales invalides."""


def _contains_sensitive_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(str(key).casefold() in SENSITIVE_KEYS or _contains_sensitive_key(item)
                   for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_sensitive_key(item) for item in value)
    return False


def validate_opportunity(opportunity: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(opportunity, dict):
        return ["L'opportunité doit être un objet."]
    missing = REQUIRED_FIELDS - set(opportunity)
    if missing:
        errors.append("Champs obligatoires absents: " + ", ".join(sorted(missing)) + ".")
    if set(opportunity) - (REQUIRED_FIELDS | {"category", "language", "notes", "platform_name"}):
        errors.append("Champs inconnus dans l'opportunité.")
    if _contains_sensitive_key(opportunity):
        errors.append("Champ sensible interdit dans une opportunité.")
    source = opportunity.get("source_url")
    if not isinstance(source, str):
        errors.append("source_url doit être une URL HTTPS.")
    else:
        parsed = urlparse(source)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            errors.append("source_url doit être une URL HTTPS publique sans identifiants.")
    if not isinstance(opportunity.get("id"), str) or not opportunity.get("id", "").strip():
        errors.append("id est obligatoire.")
    for field in ("title", "description", "currency", "country_eligibility"):
        if not isinstance(opportunity.get(field), str) or not opportunity.get(field, "").strip():
            errors.append(f"{field} doit être un texte non vide.")
    countries = opportunity.get("eligible_countries")
    if not isinstance(countries, list) or any(not isinstance(x, str) or not x.strip() for x in countries):
        errors.append("eligible_countries doit être une liste de pays.")
    for field in ("compensation_amount", "upfront_cost", "estimated_minutes"):
        value = opportunity.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            errors.append(f"{field} doit être un nombre positif ou nul.")
    if isinstance(opportunity.get("estimated_minutes"), (int, float)) and opportunity["estimated_minutes"] <= 0:
        errors.append("estimated_minutes doit être supérieur à zéro.")
    if opportunity.get("automation_policy") not in ALLOWED_AUTOMATION_POLICIES:
        errors.append("automation_policy invalide.")
    if opportunity.get("ai_policy") not in ALLOWED_AI_POLICIES:
        errors.append("ai_policy invalide.")
    if not isinstance(opportunity.get("human_presence_required"), bool):
        errors.append("human_presence_required doit être booléen.")
    methods = opportunity.get("payout_methods")
    if not isinstance(methods, list) or any(not isinstance(x, str) or not x.strip() for x in methods):
        errors.append("payout_methods doit être une liste de méthodes.")
    return errors


def evaluate_opportunity(
    opportunity: dict[str, Any],
    *,
    owner_country: str = "SN",
    accepted_payout_methods: tuple[str, ...] = (),
    require_zero_upfront_cost: bool = True,
) -> dict[str, Any]:
    """Classe une opportunité sans jamais autoriser l'envoi d'une candidature."""
    errors = validate_opportunity(opportunity)
    if errors:
        raise GlobalWorkError("; ".join(errors))

    reasons: list[str] = []
    countries = {country.casefold() for country in opportunity["eligible_countries"]}
    country_scope = opportunity["country_eligibility"].casefold()
    if owner_country.casefold() not in countries and country_scope not in {"worldwide", "global", "all countries"}:
        reasons.append("Éligibilité au pays du propriétaire non confirmée.")
    if require_zero_upfront_cost and opportunity["upfront_cost"] > 0:
        reasons.append("Coût initial non nul : exclu de la priorité sans investissement.")
    if opportunity["automation_policy"] == "prohibited":
        reasons.append("La plateforme interdit l'automatisation.")
    elif opportunity["automation_policy"] in {"human_submission_only", "unknown"}:
        reasons.append("Soumission humaine ou politique d'automatisation à vérifier.")
    if opportunity["ai_policy"] == "prohibited":
        reasons.append("L'utilisation de l'IA est interdite par les conditions indiquées.")
    elif opportunity["ai_policy"] in {"restricted", "unknown"}:
        reasons.append("Conditions d'utilisation de l'IA à vérifier.")
    if opportunity["human_presence_required"]:
        reasons.append("La mission exige une présence ou une action humaine.")
    accepted = {method.casefold() for method in accepted_payout_methods}
    offered = {method.casefold() for method in opportunity["payout_methods"]}
    if accepted and not accepted.intersection(offered):
        reasons.append("Aucun moyen de paiement compatible n'est confirmé.")

    hard_reject = (
        opportunity["automation_policy"] == "prohibited"
        or opportunity["ai_policy"] == "prohibited"
        or opportunity["human_presence_required"]
        or (require_zero_upfront_cost and opportunity["upfront_cost"] > 0)
    )
    if hard_reject:
        decision = "reject"
    elif reasons:
        decision = "manual_review"
    else:
        decision = "candidate_for_owner_policy_review"

    return {
        "opportunity_id": opportunity["id"],
        "decision": decision,
        "reasons": reasons,
        "estimated_net_amount": opportunity["compensation_amount"] - opportunity["upfront_cost"],
        "currency": opportunity["currency"],
        "estimated_minutes": opportunity["estimated_minutes"],
        "estimated_gross_per_hour": round(
            opportunity["compensation_amount"] * 60 / opportunity["estimated_minutes"], 2
        ),
        "application_submitted": False,
        "external_action_enabled": False,
        "owner_approval_required_before_application": True,
    }
