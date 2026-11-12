"""Read-only marketing campaign analysis and zero-budget experiment planning."""
from __future__ import annotations

from typing import Any

FIELDS = {
    "campaign_id", "business_line", "channel", "objective", "period_start", "period_end",
    "impressions", "clicks", "leads", "orders", "spend_xof", "paid_revenue_xof",
    "revenue_evidence_status", "source_ref",
}
CHANNELS = {"whatsapp", "instagram", "facebook", "tiktok", "linkedin", "email", "website", "referral", "offline", "other"}
OBJECTIVES = {"awareness", "traffic", "leads", "sales", "retention"}
EVIDENCE = {"unknown", "declared", "provider_confirmed"}


def _nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} doit être un entier positif ou nul.")
    return value


def _validate(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Chaque observation doit être un objet.")
    if set(raw) - FIELDS:
        raise ValueError("Champ inconnu ou donnée personnelle interdite.")
    required = {"campaign_id", "business_line", "channel", "objective", "period_start", "period_end",
                "impressions", "clicks", "leads", "orders", "spend_xof", "paid_revenue_xof"}
    if not required.issubset(raw):
        raise ValueError("Champs obligatoires manquants.")
    for field in ("campaign_id", "business_line", "period_start", "period_end"):
        if not isinstance(raw[field], str) or not raw[field].strip() or len(raw[field]) > 120:
            raise ValueError(f"{field} invalide.")
    if raw["channel"] not in CHANNELS or raw["objective"] not in OBJECTIVES:
        raise ValueError("Canal ou objectif invalide.")
    start, end = raw["period_start"], raw["period_end"]
    if len(start) != 10 or len(end) != 10 or end < start:
        raise ValueError("Période invalide : utiliser YYYY-MM-DD et une fin >= début.")
    metrics = {key: _nonnegative_int(raw[key], key) for key in
               ("impressions", "clicks", "leads", "orders", "spend_xof", "paid_revenue_xof")}
    if metrics["clicks"] > metrics["impressions"]:
        raise ValueError("Les clics ne peuvent dépasser les impressions.")
    if metrics["orders"] > metrics["leads"]:
        raise ValueError("Les commandes ne peuvent dépasser les prospects.")
    evidence = raw.get("revenue_evidence_status", "unknown")
    if evidence not in EVIDENCE:
        raise ValueError("revenue_evidence_status invalide.")
    source = raw.get("source_ref")
    if source is not None and (not isinstance(source, str) or len(source) > 300 or not source.startswith("https://")):
        raise ValueError("source_ref doit être une référence HTTPS.")
    return {
        "campaign_id": raw["campaign_id"].strip(), "business_line": raw["business_line"].strip(),
        "channel": raw["channel"], "objective": raw["objective"], "period_start": start, "period_end": end,
        **metrics, "revenue_evidence_status": evidence, "source_ref": source,
    }


def analyze_marketing_campaigns(
    observations: list[dict[str, Any]],
    *,
    monthly_budget_xof: int = 0,
) -> dict[str, Any]:
    """Analyze supplied campaign metrics; propose experiments without launching them."""
    if not isinstance(observations, list):
        raise ValueError("observations doit être une liste.")
    budget = _nonnegative_int(monthly_budget_xof, "monthly_budget_xof")
    campaigns, rejected, seen = [], [], set()
    for index, raw in enumerate(observations):
        try:
            item = _validate(raw)
            if item["campaign_id"] in seen:
                raise ValueError("Identifiant de campagne dupliqué.")
            seen.add(item["campaign_id"])
            impressions, clicks = item["impressions"], item["clicks"]
            leads, orders = item["leads"], item["orders"]
            item["ctr_percent"] = round(clicks * 100 / impressions, 2) if impressions else None
            item["lead_rate_percent"] = round(leads * 100 / clicks, 2) if clicks else None
            item["lead_to_order_percent"] = round(orders * 100 / leads, 2) if leads else None
            item["cost_per_lead_xof"] = round(item["spend_xof"] / leads, 2) if leads else None
            verified = item["revenue_evidence_status"] == "provider_confirmed"
            item["roas"] = round(item["paid_revenue_xof"] / item["spend_xof"], 2) if verified and item["spend_xof"] else None
            item["revenue_counted_as_verified"] = bool(verified)
            campaigns.append(item)
        except (TypeError, ValueError) as exc:
            rejected.append({"index": index, "reason": str(exc)})
    channel_summary = {}
    for channel in sorted(CHANNELS):
        rows = [row for row in campaigns if row["channel"] == channel]
        if rows:
            channel_summary[channel] = {
                "campaigns": len(rows),
                "impressions": sum(row["impressions"] for row in rows),
                "clicks": sum(row["clicks"] for row in rows),
                "leads": sum(row["leads"] for row in rows),
                "orders": sum(row["orders"] for row in rows),
                "spend_xof": sum(row["spend_xof"] for row in rows),
            }
    experiments = [
        {"name": "WhatsApp catalogue and status updates", "channel": "whatsapp", "budget_xof": 0,
         "test": "Présenter une offre claire à une audience ayant accepté de recevoir des messages.",
         "measure": ["conversations qualifiées", "commandes confirmées", "temps de réponse"]},
        {"name": "Referral partner pilot", "channel": "referral", "budget_xof": 0,
         "test": "Tester un apporteur d'affaires avec commission uniquement après vente encaissée et vérifiée.",
         "measure": ["prospects référés", "ventes payées", "commission due"]},
        {"name": "Organic product demonstration", "channel": "instagram", "budget_xof": 0,
         "test": "Publier une démonstration utile et mesurer les demandes entrantes sans publicité payante.",
         "measure": ["portée", "clics", "demandes qualifiées", "commandes"]},
    ]
    return {
        "status": "analyzed" if campaigns else ("rejected" if rejected else "empty"),
        "read_only": True,
        "campaigns_received": len(observations),
        "campaigns_analyzed": len(campaigns),
        "campaigns_rejected": len(rejected),
        "campaigns": campaigns,
        "channel_summary": channel_summary,
        "zero_budget_experiments": experiments,
        "monthly_budget_xof": budget,
        "budget_authorized_for_spending": False,
        "rejections": rejected,
        "limitations": [
            "Les métriques sont déclarées par l'appelant et ne sont pas extraites ni authentifiées auprès des plateformes.",
            "provider_confirmed est une étiquette fournie, pas une preuve cryptographique ou une vérification directe du prestataire.",
            "Le ROAS n'est calculé que si la preuve de revenu est marquée provider_confirmed et que la dépense est non nulle.",
            "Aucune campagne, publication, publicité, sollicitation ou dépense n'est lancée.",
        ],
    }
