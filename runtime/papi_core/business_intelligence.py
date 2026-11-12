"""Intelligence commerciale déterministe : analyse d'opportunités, sans exécution."""
from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from typing import Any

BUSINESS_LINES = {
    "PAPI MARKET", "PAPI DROPSHIPPING", "PAPI AFFILIATION",
    "PAPI FREELANCE", "PAPI SERVICES", "PAPI BUSINESS PARTNERS",
}
REQUIRED_TEXT = ("opportunity_id", "source", "source_ref", "observed_at",
                 "business_line", "market", "customer_segment", "offer")
COST_FIELDS = ("expected_price_xof", "variable_cost_xof", "acquisition_cost_xof",
               "fulfillment_cost_xof", "estimated_monthly_volume",
               "time_to_first_revenue_days", "upfront_cost_xof")
RISK_FLAGS = {"compliance", "platform_dependency", "fulfillment",
              "refunds", "supplier_reliability", "data_gaps",
              "upfront_cost", "legal_regulatory"}
RISK_POINTS = {
    "compliance": 3, "platform_dependency": 2, "fulfillment": 2,
    "refunds": 2, "supplier_reliability": 3, "data_gaps": 2,
    "upfront_cost": 2, "legal_regulatory": 4,
}


class BusinessIntelligenceError(ValueError):
    """Données d'opportunité ou politique invalides."""


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 300:
        raise BusinessIntelligenceError(f"{field} doit être un texte non vide (300 caractères maximum).")
    return value.strip()


def _number(value: Any, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BusinessIntelligenceError(f"{field} doit être un entier positif ou null.")
    return value


def _date(value: Any) -> str:
    if not isinstance(value, str):
        raise BusinessIntelligenceError("observed_at doit être une date ISO 8601.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BusinessIntelligenceError("observed_at invalide.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise BusinessIntelligenceError("observed_at doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _policy_controls(policy: dict[str, Any] | None) -> dict[str, Any]:
    if policy is not None and not isinstance(policy, dict):
        raise BusinessIntelligenceError("policy doit être un objet.")
    policy = policy or {}
    budget = policy.get("default_budget_xof", 0)
    if isinstance(budget, bool) or not isinstance(budget, int) or budget != 0:
        raise BusinessIntelligenceError("Cette phase exige un budget autorisé de 0 FCFA.")
    if policy.get("execution_enabled", False) is not False:
        raise BusinessIntelligenceError("L'exécution automatique doit rester désactivée.")
    if policy.get("external_actions_enabled", False) is not False:
        raise BusinessIntelligenceError("Les actions externes doivent rester désactivées.")
    return {"budget_xof": 0, "execution_enabled": False,
            "external_actions_enabled": False, "financial_actions_enabled": False}


def analyze_opportunity(item: dict[str, Any]) -> dict[str, Any]:
    """Analyse une fiche candidate ; toutes les projections restent hypothétiques."""
    if not isinstance(item, dict):
        raise BusinessIntelligenceError("Chaque opportunité doit être un objet.")
    normalized = {key: _text(item.get(key), key) for key in REQUIRED_TEXT}
    normalized["observed_at"] = _date(normalized["observed_at"])
    if normalized["business_line"] not in BUSINESS_LINES:
        raise BusinessIntelligenceError("business_line non reconnu.")
    numbers = {key: _number(item.get(key), key) for key in COST_FIELDS}
    evidence = item.get("evidence_refs", [])
    risks = item.get("risk_flags", [])
    if not isinstance(evidence, list) or any(not isinstance(x, str) or not x.strip() or len(x) > 300 for x in evidence):
        raise BusinessIntelligenceError("evidence_refs doit être une liste de références textuelles.")
    if not isinstance(risks, list) or any(x not in RISK_FLAGS for x in risks) or len(set(risks)) != len(risks):
        raise BusinessIntelligenceError("risk_flags contient une catégorie inconnue ou dupliquée.")

    missing = [key for key, value in numbers.items() if value is None]
    if not evidence:
        missing.append("evidence_refs")
    unit_margin = None
    if all(numbers[k] is not None for k in COST_FIELDS[:4]):
        unit_margin = (numbers["expected_price_xof"] - numbers["variable_cost_xof"]
                       - numbers["acquisition_cost_xof"] - numbers["fulfillment_cost_xof"])
    risk_score = sum(RISK_POINTS[flag] for flag in risks)
    if missing:
        recommendation = "insufficient_data"
    elif unit_margin is not None and unit_margin <= 0:
        recommendation = "reject"
    elif "legal_regulatory" in risks or "compliance" in risks or risk_score >= 9:
        recommendation = "investigate"
    elif numbers["upfront_cost_xof"] == 0 and risk_score <= 3 and numbers["time_to_first_revenue_days"] <= 30:
        recommendation = "small_test_candidate"
    else:
        recommendation = "investigate"

    scenarios = None
    break_even_units = None
    if not missing and unit_margin is not None and numbers["estimated_monthly_volume"] is not None:
        volume = numbers["estimated_monthly_volume"]
        scenarios = {
            "conservative": {"volume": volume // 2, "contribution_xof": (volume // 2) * unit_margin},
            "base": {"volume": volume, "contribution_xof": volume * unit_margin},
            "upside": {"volume": ceil(volume * 1.5), "contribution_xof": ceil(volume * 1.5) * unit_margin},
            "basis": "hypothetical_monthly_contribution_before_fixed_costs_and_tax",
        }
        if unit_margin > 0:
            break_even_units = ceil(numbers["upfront_cost_xof"] / unit_margin)

    return {
        **normalized, **numbers, "evidence_refs": evidence, "risk_flags": risks,
        "missing_inputs": missing, "unit_contribution_xof": unit_margin,
        "break_even_units": break_even_units, "risk_score": risk_score,
        "risk_level": "high" if risk_score >= 7 else "moderate" if risk_score >= 4 else "low",
        "scenarios": scenarios, "recommendation": recommendation,
        "assumptions": ["Les volumes, prix et coûts sont des estimations fournies, non vérifiées.",
                        "Les scénarios ne sont ni des ventes ni du chiffre d'affaires réalisé.",
                        "Les projections excluent impôts et coûts fixes non fournis."],
        "realized_revenue_xof": None,
        "evidence_status": "provided_not_independently_verified",
    }


def build_business_intelligence(opportunities: list[dict[str, Any]],
                                policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Construit un portefeuille d'opportunités et des plans candidats, en lecture seule."""
    if not isinstance(opportunities, list):
        raise BusinessIntelligenceError("opportunities doit être une liste.")
    controls = _policy_controls(policy)
    reports, seen = [], set()
    for item in opportunities:
        report = analyze_opportunity(item)
        if report["opportunity_id"] in seen:
            raise BusinessIntelligenceError("Identifiant d'opportunité dupliqué.")
        seen.add(report["opportunity_id"])
        reports.append(report)
    reports.sort(key=lambda x: ({"small_test_candidate": 0, "investigate": 1,
                                 "insufficient_data": 2, "reject": 3}[x["recommendation"]],
                                x["risk_score"], x["opportunity_id"]))
    plans = []
    for report in reports:
        if report["recommendation"] in {"small_test_candidate", "investigate"}:
            plans.append({
                "plan_id": "candidate:" + report["opportunity_id"],
                "opportunity_id": report["opportunity_id"],
                "status": "proposal_only",
                "milestones": [
                    {"step": 1, "owner_role": "Astou", "action": "Vérifier les preuves et les hypothèses de marché."},
                    {"step": 2, "owner_role": "Marietou Diouf", "action": "Examiner les risques, coûts et conformité."},
                    {"step": 3, "owner_role": "Owner", "action": "Décider explicitement si un test limité peut être autorisé."},
                ],
                "execution_authorized": False,
            })
    return {
        "status": "available" if reports else "no_opportunities",
        "source": "manually_supplied_opportunity_candidates",
        "opportunities_total": len(reports),
        "summary": {key: sum(x["recommendation"] == key for x in reports)
                    for key in ("small_test_candidate", "investigate", "insufficient_data", "reject")},
        "opportunities": reports, "action_plan_candidates": plans,
        "controls": {**controls, "read_only": True, "opportunity_scans_performed": 0,
                     "external_research_performed": False, "messages_sent": 0,
                     "purchases_made": 0, "spending_xof": 0,
                     "tasks_created": 0, "actions_executed": 0,
                     "realized_revenue_recorded": 0},
    }
