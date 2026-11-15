"""Zero-upfront-cost channel eligibility and routing for PAPI KIDS.

The router is deliberately evidence-gated. Unknown country, payout, format,
fee or fulfilment facts result in HOLD, never an optimistic recommendation.
It performs no network calls, account actions, purchases or publication.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PLATFORMS = ("amazon_kdp", "lulu", "ingramspark", "bookvault", "blurb", "jumia_senegal")
FACT_STATES = {"verified", "blocked", "unknown"}
BOOK_FORMATS = {"paperback", "ebook", "coloring_book", "illustrated_book", "activity_book"}
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FILE = ROOT / "data" / "divisions" / "papi-kids-channel-profiles.json"


class KidsChannelRoutingError(ValueError):
    """Invalid channel profile or routing request."""


def _is_nonnegative_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def validate_profiles(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict) or set(data) != {"schema_version", "division_id", "profiles"}:
        return ["Le registre doit contenir schema_version, division_id et profiles."]
    if data["schema_version"] != 1 or data["division_id"] != "papi_kids_publishing":
        errors.append("Version ou division invalide.")
    profiles = data["profiles"]
    if not isinstance(profiles, list):
        return errors + ["profiles doit être une liste."]
    seen: set[str] = set()
    required = {
        "platform_id", "name", "formats", "senegal_seller_eligibility",
        "senegal_payout", "territory_coverage", "upfront_cost_xof",
        "subscription_required", "seller_funds_each_order", "stock_required",
        "direct_print_fulfilment", "evidence", "last_verified",
    }
    for index, profile in enumerate(profiles):
        label = f"Plateforme #{index + 1}"
        if not isinstance(profile, dict) or set(profile) != required:
            errors.append(f"{label}: structure de profil invalide.")
            continue
        pid = profile["platform_id"]
        if not isinstance(pid, str) or pid not in PLATFORMS:
            errors.append(f"{label}: platform_id inconnu.")
        elif pid in seen:
            errors.append(f"{label}: plateforme dupliquée.")
        else:
            seen.add(pid)
        if not isinstance(profile["name"], str) or not profile["name"].strip():
            errors.append(f"{label}: nom obligatoire.")
        if not isinstance(profile["formats"], list) or any(x not in BOOK_FORMATS for x in profile["formats"]):
            errors.append(f"{label}: formats invalides.")
        for field in ("senegal_seller_eligibility", "senegal_payout", "territory_coverage",
                      "subscription_required", "seller_funds_each_order", "stock_required",
                      "direct_print_fulfilment"):
            if profile[field] not in FACT_STATES:
                errors.append(f"{label}: {field} doit être verified, blocked ou unknown.")
        if not _is_nonnegative_number(profile["upfront_cost_xof"]):
            errors.append(f"{label}: upfront_cost_xof doit être un nombre positif ou nul.")
        if not isinstance(profile["evidence"], list):
            errors.append(f"{label}: evidence doit être une liste.")
        if not isinstance(profile["last_verified"], str):
            errors.append(f"{label}: last_verified doit être une chaîne.")
    if seen != set(PLATFORMS):
        errors.append("Le registre doit contenir exactement les six plateformes prévues.")
    return errors


def load_profiles(path: Path = DEFAULT_FILE) -> dict[str, Any]:
    try:
        if path.is_symlink() or path.stat().st_size > 512 * 1024:
            raise KidsChannelRoutingError("Fichier symbolique ou trop volumineux.")
        data = json.loads(path.read_text(encoding="utf-8"))
    except KidsChannelRoutingError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise KidsChannelRoutingError("Registre de canaux absent ou JSON invalide.") from exc
    errors = validate_profiles(data)
    if errors:
        raise KidsChannelRoutingError("; ".join(errors))
    return data


def assess_channel(profile: dict[str, Any], book_format: str, target_country: str = "SN") -> dict[str, Any]:
    """Return ELIGIBLE only when every zero-cash and access gate is verified."""
    if book_format not in BOOK_FORMATS:
        raise KidsChannelRoutingError("Format de livre non pris en charge.")
    if target_country != "SN":
        raise KidsChannelRoutingError("Cette version évalue uniquement le pays vendeur Sénégal (SN).")
    gates = {
        "seller_eligibility": profile["senegal_seller_eligibility"],
        "payout_to_senegal": profile["senegal_payout"],
        "territory_delivery": profile["territory_coverage"],
        "format": "verified" if book_format in profile["formats"] else "blocked",
        "no_subscription": "blocked" if profile["subscription_required"] == "verified" else profile["subscription_required"],
        "no_per_order_advance": "blocked" if profile["seller_funds_each_order"] == "verified" else profile["seller_funds_each_order"],
        "no_stock": "blocked" if profile["stock_required"] == "verified" else profile["stock_required"],
        "direct_print_fulfilment": profile["direct_print_fulfilment"],
        "zero_upfront_cost": "verified" if profile["upfront_cost_xof"] == 0 else "blocked",
    }
    blocked = [name for name, state in gates.items() if state == "blocked"]
    unknown = [name for name, state in gates.items() if state == "unknown"]
    status = "BLOCKED" if blocked else "HOLD" if unknown else "ELIGIBLE_ZERO_UPFRONT"
    return {
        "platform_id": profile["platform_id"],
        "name": profile["name"],
        "status": status,
        "gates": gates,
        "blocked_reasons": blocked,
        "facts_to_verify": unknown,
        "upfront_cost_xof": profile["upfront_cost_xof"],
        "evidence": profile["evidence"],
        "last_verified": profile["last_verified"],
        "publication_authorized": False,
    }


def build_routing_report(book_format: str, target_country: str = "SN",
                         path: Path = DEFAULT_FILE) -> dict[str, Any]:
    data = load_profiles(path)
    results = [assess_channel(profile, book_format, target_country) for profile in data["profiles"]]
    eligible = [item for item in results if item["status"] == "ELIGIBLE_ZERO_UPFRONT"]
    return {
        "division_id": data["division_id"],
        "book_format": book_format,
        "seller_country": target_country,
        "budget_policy": "ZERO_UPFRONT_XOF",
        "eligible_channels": eligible,
        "hold_channels": [item for item in results if item["status"] == "HOLD"],
        "blocked_channels": [item for item in results if item["status"] == "BLOCKED"],
        "recommended_channel": eligible[0]["platform_id"] if eligible else None,
        "decision": "REVIEW_ELIGIBLE_CHANNELS" if eligible else "NO_VERIFIED_ZERO_COST_CHANNEL",
        "publication_authorized": False,
        "external_actions_performed": False,
    }
