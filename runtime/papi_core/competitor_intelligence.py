"""Analyse comparative de concurrents à partir d'observations publiques fournies."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse


class CompetitorIntelligenceError(ValueError):
    """Observation concurrentielle invalide."""


SOURCE_QUALITY = {"official_public_page": 3, "public_catalog": 3,
                 "public_ad": 2, "public_social_post": 2,
                 "user_observation": 1}


def _required_text(value: Any, field: str, limit: int = 300) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise CompetitorIntelligenceError(f"{field} doit être un texte non vide ({limit} caractères maximum).")
    return value.strip()


def _optional_amount(value: Any, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CompetitorIntelligenceError(f"{field} doit être un entier positif ou null.")
    return value


def _parse_date(value: Any) -> datetime:
    if not isinstance(value, str):
        raise CompetitorIntelligenceError("observed_at doit être une date ISO 8601.")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CompetitorIntelligenceError("observed_at invalide.") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise CompetitorIntelligenceError("observed_at doit inclure un fuseau horaire.")
    return result.astimezone(timezone.utc)


def _public_source_url(value: Any) -> str:
    url = _required_text(value, "source_url", 1000)
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise CompetitorIntelligenceError("source_url doit être une URL HTTPS publique sans identifiants.")
    if parsed.scheme == "https" and (parsed.hostname or "").lower() in {"localhost", "127.0.0.1"}:
        raise CompetitorIntelligenceError("source_url locale interdite.")
    return url


def analyze_competitor_observations(
    observations: list[dict[str, Any]], *, as_of: str,
    own_price_xof: int | None = None, freshness_days: int = 30,
) -> dict[str, Any]:
    """Compare les données observées ; ne visite aucune URL et ne suppose rien."""
    if not isinstance(observations, list):
        raise CompetitorIntelligenceError("observations doit être une liste.")
    if isinstance(freshness_days, bool) or not isinstance(freshness_days, int) or not 1 <= freshness_days <= 365:
        raise CompetitorIntelligenceError("freshness_days doit être compris entre 1 et 365.")
    own_price = _optional_amount(own_price_xof, "own_price_xof")
    cutoff = _parse_date(as_of)
    results, rejected, seen = [], [], set()
    for index, raw in enumerate(observations):
        try:
            if not isinstance(raw, dict):
                raise CompetitorIntelligenceError("L'observation doit être un objet.")
            required = {"competitor_name", "market", "offer", "source_type",
                        "source_url", "observed_at", "price_xof"}
            optional = {"currency", "notes"}
            if not required.issubset(raw) or set(raw) - required - optional:
                raise CompetitorIntelligenceError("Champs manquants ou inconnus.")
            competitor = _required_text(raw["competitor_name"], "competitor_name")
            market = _required_text(raw["market"], "market")
            offer = _required_text(raw["offer"], "offer")
            source_type = _required_text(raw["source_type"], "source_type")
            if source_type not in SOURCE_QUALITY:
                raise CompetitorIntelligenceError("source_type non reconnu.")
            source_url = _public_source_url(raw["source_url"])
            observed = _parse_date(raw["observed_at"])
            if observed > cutoff:
                raise CompetitorIntelligenceError("Observation datée dans le futur.")
            price = _optional_amount(raw["price_xof"], "price_xof")
            currency = raw.get("currency", "XOF")
            if currency != "XOF":
                raise CompetitorIntelligenceError("Seuls les prix explicitement exprimés en XOF sont comparables.")
            notes = raw.get("notes", "")
            if not isinstance(notes, str) or len(notes) > 500:
                raise CompetitorIntelligenceError("notes doit être un texte de 500 caractères maximum.")
            key = (competitor.casefold(), market.casefold(), offer.casefold(), source_url, observed.isoformat())
            if key in seen:
                continue
            seen.add(key)
            age_days = (cutoff - observed).days
            fresh = age_days <= freshness_days
            delta = None
            delta_pct = None
            if own_price is not None and price is not None and own_price > 0:
                delta = price - own_price
                delta_pct = round((delta / own_price) * 100, 2)
            quality = SOURCE_QUALITY[source_type]
            results.append({
                "competitor_name": competitor, "market": market, "offer": offer,
                "source_type": source_type, "source_url": source_url,
                "observed_at": observed.isoformat().replace("+00:00", "Z"),
                "age_days": age_days, "fresh": fresh,
                "price_xof": price, "currency": "XOF",
                "price_difference_vs_own_xof": delta,
                "price_difference_vs_own_percent": delta_pct,
                "source_quality_score": quality,
                "confidence": "moderate" if fresh and quality == 3 else "low",
                "notes": notes,
                "evidence_status": "public_source_reference_provided_not_fetched_or_verified",
            })
        except (CompetitorIntelligenceError, TypeError, KeyError) as exc:
            rejected.append({"index": index, "reason": str(exc)})
    results.sort(key=lambda x: (not x["fresh"], -x["source_quality_score"],
                                x["competitor_name"].casefold(), x["offer"].casefold()))
    return {
        "status": "available" if results else "no_valid_observations",
        "source": "user_supplied_public_competitor_observations",
        "observations_received": len(observations),
        "observations_analyzed": len(results),
        "observations_rejected": len(rejected),
        "observations": results,
        "rejections": rejected,
        "limitations": [
            "Aucune URL n'est visitée ; le contenu et le prix ne sont pas vérifiés indépendamment.",
            "Les prix ne sont comparés que si les montants sont explicitement en XOF.",
            "Les offres peuvent différer par périmètre, qualité, taxes ou conditions.",
            "Un échantillon limité ne représente pas l'ensemble du marché.",
        ],
        "controls": {"network_requests": 0, "pages_fetched": 0,
                     "messages_sent": 0, "spending_xof": 0,
                     "actions_executed": 0, "read_only": True},
    }
