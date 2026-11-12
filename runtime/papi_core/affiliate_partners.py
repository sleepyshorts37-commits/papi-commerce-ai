"""Read-only affiliate partner and attributed commission analysis."""
from __future__ import annotations

from typing import Any

FIELDS = {
    "partner_id", "referral_id", "sale_id", "business_line", "channel",
    "referred_at", "referral_status", "sale_status", "order_value_xof",
    "commission_rate_bps", "payment_evidence_status", "sale_at",
}
CHANNELS = {"whatsapp", "instagram", "facebook", "tiktok", "email", "website", "offline", "other"}
REFERRAL_STATUSES = {"referred", "qualified", "converted", "lost"}
SALE_STATUSES = {"none", "pending", "paid", "cancelled"}
EVIDENCE = {"unknown", "declared", "provider_confirmed"}


def _timestamp(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 40:
        raise ValueError(f"{field} invalide.")
    from datetime import datetime
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} doit être une date ISO 8601.") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} doit inclure un fuseau horaire.")
    return value


def _integer(value: Any, field: str, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} doit être un entier positif ou nul.")
    if maximum is not None and value > maximum:
        raise ValueError(f"{field} dépasse la limite autorisée.")
    return value


def _validate(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Chaque enregistrement doit être un objet.")
    if set(raw) - FIELDS:
        raise ValueError("Champ inconnu ou donnée personnelle interdite.")
    required = {"partner_id", "referral_id", "business_line", "channel", "referred_at",
                "referral_status", "sale_status", "order_value_xof", "commission_rate_bps"}
    if not required.issubset(raw):
        raise ValueError("Champs obligatoires manquants.")
    for field in ("partner_id", "referral_id", "business_line"):
        value = raw[field]
        if not isinstance(value, str) or not value.strip() or len(value) > 120:
            raise ValueError(f"{field} invalide.")
    if raw["channel"] not in CHANNELS:
        raise ValueError("Canal invalide.")
    if raw["referral_status"] not in REFERRAL_STATUSES or raw["sale_status"] not in SALE_STATUSES:
        raise ValueError("Statut de recommandation ou de vente invalide.")
    value = _integer(raw["order_value_xof"], "order_value_xof")
    rate = _integer(raw["commission_rate_bps"], "commission_rate_bps", 10000)
    referred_at = _timestamp(raw["referred_at"], "referred_at")
    sale_at = raw.get("sale_at")
    if sale_at is not None:
        sale_at = _timestamp(sale_at, "sale_at")
    sale_id = raw.get("sale_id")
    if raw["sale_status"] in {"pending", "paid", "cancelled"}:
        if not isinstance(sale_id, str) or not sale_id.strip() or len(sale_id) > 120:
            raise ValueError("sale_id obligatoire pour une vente.")
    elif sale_id is not None:
        raise ValueError("sale_id doit être absent si sale_status vaut none.")
    if raw["sale_status"] == "none" and value != 0:
        raise ValueError("Une recommandation sans vente doit avoir order_value_xof à zéro.")
    if raw["sale_status"] in {"none", "pending", "cancelled"} and raw["referral_status"] == "converted":
        raise ValueError("Une recommandation convertie doit correspondre à une vente payée.")
    if raw["sale_status"] == "paid" and raw["referral_status"] != "converted":
        raise ValueError("Une vente payée doit avoir referral_status=converted.")
    evidence = raw.get("payment_evidence_status", "unknown")
    if evidence not in EVIDENCE:
        raise ValueError("payment_evidence_status invalide.")
    return {
        "partner_id": raw["partner_id"].strip(), "referral_id": raw["referral_id"].strip(),
        "sale_id": sale_id.strip() if isinstance(sale_id, str) else None,
        "business_line": raw["business_line"].strip(), "channel": raw["channel"],
        "referred_at": referred_at, "sale_at": sale_at,
        "referral_status": raw["referral_status"], "sale_status": raw["sale_status"],
        "order_value_xof": value, "commission_rate_bps": rate,
        "payment_evidence_status": evidence,
    }


def analyze_affiliate_partners(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze supplied anonymized referral/sale snapshots; never pays commissions."""
    if not isinstance(records, list):
        raise ValueError("records doit être une liste.")
    analyzed, rejected, referral_ids, sale_ids = [], [], set(), set()
    for index, raw in enumerate(records):
        try:
            item = _validate(raw)
            if item["referral_id"] in referral_ids:
                raise ValueError("Identifiant de recommandation dupliqué.")
            if item["sale_id"] is not None and item["sale_id"] in sale_ids:
                raise ValueError("Identifiant de vente dupliqué.")
            referral_ids.add(item["referral_id"])
            if item["sale_id"] is not None:
                sale_ids.add(item["sale_id"])
            verified = item["sale_status"] == "paid" and item["payment_evidence_status"] == "provider_confirmed"
            item["commission_estimate_xof"] = (
                (item["order_value_xof"] * item["commission_rate_bps"] + 5000) // 10000
                if verified else None
            )
            item["commission_estimate_is_provisional"] = bool(verified)
            item["payment_evidence_independently_verified"] = False
            analyzed.append(item)
        except (TypeError, ValueError) as exc:
            rejected.append({"index": index, "reason": str(exc)})
    partner_summary = {}
    for partner_id in sorted({row["partner_id"] for row in analyzed}):
        rows = [row for row in analyzed if row["partner_id"] == partner_id]
        paid_verified = [row for row in rows if row["commission_estimate_xof"] is not None]
        partner_summary[partner_id] = {
            "referrals": len(rows),
            "qualified_referrals": sum(row["referral_status"] == "qualified" for row in rows),
            "converted_referrals": sum(row["referral_status"] == "converted" for row in rows),
            "conversion_rate_percent": round(
                sum(row["referral_status"] == "converted" for row in rows) * 100 / len(rows), 2
            ) if rows else 0,
            "verified_paid_sale_candidates": len(paid_verified),
            "provisional_commission_estimate_xof": sum(row["commission_estimate_xof"] for row in paid_verified),
        }
    provisional_total = sum(
        row["commission_estimate_xof"] for row in analyzed if row["commission_estimate_xof"] is not None
    )
    return {
        "status": "analyzed" if analyzed else ("rejected" if rejected else "empty"),
        "read_only": True,
        "records_received": len(records),
        "records_analyzed": len(analyzed),
        "records_rejected": len(rejected),
        "partners_analyzed": len(partner_summary),
        "referrals_analyzed": len(analyzed),
        "converted_referrals": sum(row["referral_status"] == "converted" for row in analyzed),
        "verified_paid_sale_candidates": sum(row["commission_estimate_xof"] is not None for row in analyzed),
        "provisional_commission_estimate_xof": provisional_total,
        "commission_records": analyzed,
        "partner_summary": partner_summary,
        "rejections": rejected,
        "limitations": [
            "Les instantanés sont fournis par l'appelant ; les statuts de paiement ne sont pas authentifiés directement auprès du prestataire.",
            "provider_confirmed est une déclaration fournie, pas une preuve cryptographique ni une vérification indépendante.",
            "Les commissions affichées sont des estimations provisoires, non une dette exigible ni une validation comptable ou contractuelle.",
            "Aucun partenaire n'est contacté ; aucun paiement, transfert, retrait, décaissement ou changement de contrat n'est effectué.",
            "Les identifiants partenaires doivent être opaques ; noms, téléphones, e-mails, coordonnées de paiement et données clients sont interdits.",
        ],
        "payouts_executed": 0,
        "partner_contacts_sent": 0,
    }
