"""Read-only scoring of commercial opportunities; no external actions."""
from __future__ import annotations

from typing import Any

# Weights total 100. Higher values mean a more attractive, validated opportunity.
WEIGHTS = {
    "senegal_access": 20,
    "zero_cost_start": 15,
    "time_to_first_revenue": 15,
    "net_margin": 15,
    "demand_evidence": 15,
    "low_risk": 10,
    "operational_fit": 10,
}
ALLOWED_DECISIONS = {"test", "investigate", "hold", "reject"}
MAX_TEXT = 500


def _score(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 5:
        raise ValueError(f"{field} doit être un entier de 0 à 5.")
    return value


def _text(value: Any, field: str, required: bool = True) -> str:
    if not isinstance(value, str) or (required and not value.strip()) or len(value) > MAX_TEXT:
        raise ValueError(f"{field} invalide.")
    return value.strip()


def score_opportunity(raw: dict[str, Any]) -> dict[str, Any]:
    """Score one opportunity from explicit evidence supplied by the caller.

    A high score never overrides a failed eligibility, legality, or evidence gate.
    The function does not browse, contact, buy, publish, or execute experiments.
    """
    if not isinstance(raw, dict):
        raise ValueError("L'opportunité doit être un objet.")
    allowed = {"opportunity_id", "title", "source", "source_checked_at", "country_access",
               "legal_status", "payment_access", "evidence_level", "criteria", "estimated_startup_cost_xof",
               "estimated_days_to_first_revenue", "estimated_net_margin_percent", "notes"}
    if set(raw) - allowed:
        raise ValueError("Champ inconnu ; ne pas inclure de données personnelles.")
    required = allowed - {"notes"}
    if not required.issubset(raw):
        raise ValueError("Champs obligatoires manquants.")
    opportunity_id = _text(raw["opportunity_id"], "opportunity_id")
    title = _text(raw["title"], "title")
    source = _text(raw["source"], "source")
    checked_at = _text(raw["source_checked_at"], "source_checked_at")
    country_access = raw["country_access"]
    legal_status = raw["legal_status"]
    payment_access = raw["payment_access"]
    evidence_level = raw["evidence_level"]
    if country_access not in {"confirmed", "uncertain", "unavailable"}:
        raise ValueError("country_access invalide.")
    if legal_status not in {"compliant", "uncertain", "prohibited"}:
        raise ValueError("legal_status invalide.")
    if payment_access not in {"confirmed", "uncertain", "unavailable"}:
        raise ValueError("payment_access invalide.")
    if evidence_level not in {"verified", "partially_verified", "unverified"}:
        raise ValueError("evidence_level invalide.")
    criteria = raw["criteria"]
    if not isinstance(criteria, dict) or set(criteria) != set(WEIGHTS):
        raise ValueError("criteria doit contenir exactement les sept critères attendus.")
    values = {key: _score(criteria[key], key) for key in WEIGHTS}
    cost = raw["estimated_startup_cost_xof"]
    days = raw["estimated_days_to_first_revenue"]
    margin = raw["estimated_net_margin_percent"]
    for value, field in ((cost, "estimated_startup_cost_xof"), (days, "estimated_days_to_first_revenue")):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{field} doit être un entier positif ou nul.")
    if isinstance(margin, bool) or not isinstance(margin, (int, float)) or not 0 <= margin <= 100:
        raise ValueError("estimated_net_margin_percent doit être compris entre 0 et 100.")
    notes = _text(raw.get("notes", ""), "notes", required=False)

    weighted = sum(values[key] * weight for key, weight in WEIGHTS.items())
    score = round(weighted / 5)
    blockers = []
    if country_access != "confirmed":
        blockers.append("Accès depuis le Sénégal non confirmé.")
    if legal_status != "compliant":
        blockers.append("Conformité légale et règles de plateforme non confirmées.")
    if payment_access != "confirmed":
        blockers.append("Moyen de paiement et retrait non confirmé depuis le Sénégal.")
    if evidence_level == "unverified":
        blockers.append("Sources ou conditions essentielles non vérifiées.")
    if blockers or legal_status == "prohibited" or country_access == "unavailable" or payment_access == "unavailable":
        decision = "hold" if legal_status != "prohibited" else "reject"
    elif score >= 75:
        decision = "test"
    elif score >= 55:
        decision = "investigate"
    elif score >= 35:
        decision = "hold"
    else:
        decision = "reject"

    return {
        "opportunity_id": opportunity_id,
        "title": title,
        "score": score,
        "decision": decision,
        "weighted_criteria": {key: {"score_0_to_5": values[key], "weight": WEIGHTS[key]} for key in WEIGHTS},
        "gate_status": {
            "country_access": country_access,
            "legal_status": legal_status,
            "payment_access": payment_access,
            "evidence_level": evidence_level,
            "blockers": blockers,
        },
        "estimates": {
            "startup_cost_xof": cost,
            "days_to_first_revenue": days,
            "net_margin_percent": margin,
            "are_forecasts_not_results": True,
        },
        "source": source,
        "source_checked_at": checked_at,
        "notes": notes,
        "read_only": True,
        "execution_authorized": False,
        "limitations": [
            "Le score dépend des notes et éléments fournis ; il ne constitue pas une vérification indépendante.",
            "Les estimations ne sont ni des ventes ni des revenus garantis.",
            "Aucune dépense, inscription, prise de contact, commande ou opération financière n'est exécutée.",
        ],
    }


def rank_opportunities(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Score supplied opportunities and return the top three eligible candidates."""
    if not isinstance(records, list):
        raise ValueError("records doit être une liste.")
    results = []
    rejected_inputs = []
    for index, raw in enumerate(records):
        try:
            results.append(score_opportunity(raw))
        except (TypeError, ValueError) as exc:
            rejected_inputs.append({"index": index, "reason": str(exc)})
    results.sort(key=lambda item: (item["decision"] == "test", item["score"]), reverse=True)
    return {
        "status": "ranked" if results else ("rejected" if rejected_inputs else "empty"),
        "read_only": True,
        "opportunities_received": len(records),
        "opportunities_scored": len(results),
        "inputs_rejected": len(rejected_inputs),
        "top_three": [item for item in results if item["decision"] in {"test", "investigate"}][:3],
        "all_ranked": results,
        "rejections": rejected_inputs,
        "execution_authorized": False,
    }
