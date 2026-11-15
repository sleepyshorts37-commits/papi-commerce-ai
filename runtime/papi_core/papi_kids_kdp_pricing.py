"""Date-stamped estimate calculator for KDP paperback color printing and royalties."""
from __future__ import annotations

from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from typing import Any


class KDPPriceError(ValueError):
    """Unsupported KDP configuration or list price."""


# Figures transcribed from the official KDP paperback printing-cost and royalty pages,
# checked 2026-11-15. These are estimates; KDP's Rights & Pricing screen is authoritative.
MARKETPLACES = {
    "amazon.com": {
        "currency": "USD", "threshold_50": "9.98", "threshold_60": "9.99",
        "maximum": "250", "regular": {"premium_24_40": "3.60", "premium_fixed": "1.00", "premium_page": "0.065",
            "standard_fixed": "1.00", "standard_page": "0.0255"},
        "large": {"premium_24_40": "4.20", "premium_fixed": "1.00", "premium_page": "0.080",
            "standard_fixed": "1.00", "standard_page": "0.0402"},
    },
    "amazon.ca": {
        "currency": "CAD", "threshold_50": "13.98", "threshold_60": "13.99",
        "maximum": "350", "regular": {"premium_24_40": "4.66", "premium_fixed": "1.26", "premium_page": "0.085",
            "standard_fixed": "1.26", "standard_page": "0.037"},
        "large": {"premium_24_40": "5.26", "premium_fixed": "1.26", "premium_page": "0.100",
            "standard_fixed": "1.26", "standard_page": "0.052"},
    },
    "amazon.co.uk": {
        "currency": "GBP", "threshold_50": "7.98", "threshold_60": "7.99",
        "maximum": "250", "regular": {"premium_24_40": "2.59", "premium_fixed": "0.85", "premium_page": "0.0435",
            "standard_fixed": "0.85", "standard_page": "0.020"},
        "large": {"premium_24_40": "3.24", "premium_fixed": "0.85", "premium_page": "0.0598",
            "standard_fixed": "0.85", "standard_page": "0.027"},
    },
    "amazon.eu": {
        "currency": "EUR", "threshold_50": "9.98", "threshold_60": "9.99",
        "maximum": "250", "regular": {"premium_24_40": "2.85", "premium_fixed": "0.75", "premium_page": "0.0525",
            "standard_fixed": "0.75", "standard_page": "0.024"},
        "large": {"premium_24_40": "3.61", "premium_fixed": "0.75", "premium_page": "0.0715",
            "standard_fixed": "0.75", "standard_page": "0.035"},
    },
    "amazon.pl": {
        "currency": "PLN", "threshold_50": "39", "threshold_60": "40",
        "maximum": "1200", "regular": {"premium_24_40": "12.86", "premium_fixed": "3.51", "premium_page": "0.267",
            "standard_fixed": "3.51", "standard_page": "0.112"},
        "large": {"premium_24_40": "15.32", "premium_fixed": "3.51", "premium_page": "0.337",
            "standard_fixed": "3.51", "standard_page": "0.164"},
    },
    "amazon.se": {
        "currency": "SEK", "threshold_50": "109", "threshold_60": "110",
        "maximum": "2500", "regular": {"premium_24_40": "30.65", "premium_fixed": "8.37", "premium_page": "0.636",
            "standard_fixed": "8.37", "standard_page": "0.268"},
        "large": {"premium_24_40": "36.51", "premium_fixed": "8.37", "premium_page": "0.804",
            "standard_fixed": "8.37", "standard_page": "0.3691"},
    },
    "amazon.com.au": {
        "currency": "AUD", "threshold_50": "13.98", "threshold_60": "13.99",
        "maximum": "350", "regular": {"premium_24_40": "5.82", "premium_fixed": "2.42", "premium_page": "0.085",
            "standard_fixed": "2.42", "standard_page": "0.0209"},
        "large": {"premium_24_40": "6.42", "premium_fixed": "2.42", "premium_page": "0.100",
            "standard_fixed": "2.42", "standard_page": "0.0257"},
    },
    "amazon.co.jp": {
        "currency": "JPY", "threshold_50": "999", "threshold_60": "1000",
        "maximum": "30000", "regular": {"premium_24_40": "475", "premium_fixed": "206", "premium_page": "4",
            "standard_fixed": "206", "standard_page": "3.5"},
        "large": {"premium_24_40": "475", "premium_fixed": "206", "premium_page": "5",
            "standard_fixed": "206", "standard_page": "4.5"},
    },
}

SOURCE_PRINT = "https://kdp.amazon.com/en_US/help/topic/G201834340"
SOURCE_ROYALTY = "https://kdp.amazon.com/en_US/help/topic/G201834330"
SOURCE_CHECKED_AT = "2026-11-15"


def _money(value: Decimal, currency: str, rounding=ROUND_HALF_UP) -> Decimal:
    quantum = Decimal("1") if currency == "JPY" else Decimal("0.01")
    return value.quantize(quantum, rounding=rounding)


def calculate_paperback_price(
    *,
    marketplace: str,
    page_count: int,
    trim_width_in: float,
    trim_height_in: float,
    color_mode: str,
    list_price: str | int | float,
    expanded_distribution: bool = False,
) -> dict[str, Any]:
    """Estimate print cost and royalty using KDP's published marketplace tables."""
    config = MARKETPLACES.get(marketplace)
    if not config:
        raise KDPPriceError("Marketplace non pris en charge par la table vérifiée.")
    if not isinstance(page_count, int) or isinstance(page_count, bool) or page_count < 24 or page_count % 2:
        raise KDPPriceError("La pagination doit être paire et compter au moins 24 pages.")
    if color_mode not in {"premium_color", "standard_color"}:
        raise KDPPriceError("Seuls les modes couleur sont pris en charge.")
    if color_mode == "premium_color" and not 24 <= page_count <= 828:
        raise KDPPriceError("Pagination hors plage premium color.")
    if color_mode == "standard_color" and not 72 <= page_count <= 600:
        raise KDPPriceError("Le standard color exige 72 à 600 pages.")
    large = float(trim_width_in) > 6.12 or float(trim_height_in) > 9.0
    band = config["large" if large else "regular"]
    if color_mode == "premium_color" and page_count <= 40:
        print_cost = Decimal(band["premium_24_40"])
        print_formula = "fixed_cost_only_for_24_to_40_premium_color_pages"
    elif color_mode == "premium_color":
        print_cost = Decimal(band["premium_fixed"]) + Decimal(page_count) * Decimal(band["premium_page"])
        print_formula = "fixed_cost_plus_page_count_times_premium_per_page"
    else:
        print_cost = Decimal(band["standard_fixed"]) + Decimal(page_count) * Decimal(band["standard_page"])
        print_formula = "fixed_cost_plus_page_count_times_standard_per_page"

    try:
        price = Decimal(str(list_price))
    except Exception as exc:
        raise KDPPriceError("Prix catalogue invalide.") from exc
    if not price.is_finite() or price <= 0 or price > Decimal(config["maximum"]):
        raise KDPPriceError("Prix catalogue hors limites.")
    threshold_50 = Decimal(config["threshold_50"])
    threshold_60 = Decimal(config["threshold_60"])
    if price <= threshold_50:
        rate = Decimal("0.50")
    elif price >= threshold_60:
        rate = Decimal("0.60")
    else:
        raise KDPPriceError("Le prix est dans l'intervalle de seuil non autorisé par KDP.")

    # Determine the lowest price that covers print cost in either royalty tier.
    unit = Decimal("1") if config["currency"] == "JPY" else Decimal("0.01")
    if expanded_distribution:
        minimum_price = print_cost / Decimal("0.40")
    else:
        minimum_50 = print_cost / Decimal("0.50")
        if minimum_50 <= threshold_50:
            minimum_price = minimum_50
        else:
            minimum_price = max(threshold_60, print_cost / Decimal("0.60"))
    minimum_price = (minimum_price / unit).to_integral_value(rounding=ROUND_CEILING) * unit
    if price < minimum_price:
        raise KDPPriceError(f"Prix inférieur au minimum estimé KDP ({minimum_price} {config['currency']}).")

    royalty_rate = Decimal("0.40") if expanded_distribution else rate
    royalty = royalty_rate * price - print_cost
    if royalty < 0:
        raise KDPPriceError("La redevance estimée serait négative.")
    return {
        "marketplace": marketplace,
        "currency": config["currency"],
        "page_count": page_count,
        "trim_class": "large" if large else "regular",
        "color_mode": color_mode,
        "printing_cost": str(_money(print_cost, config["currency"])),
        "list_price": str(_money(price, config["currency"])),
        "royalty_rate": str(royalty_rate),
        "estimated_royalty": str(_money(royalty, config["currency"])),
        "minimum_list_price_estimate": str(_money(minimum_price, config["currency"], ROUND_CEILING)),
        "expanded_distribution": expanded_distribution,
        "formula": "(royalty_rate × list_price) − printing_cost",
        "printing_cost_formula": print_formula,
        "taxes_included": False,
        "currency_conversion_performed": False,
        "estimate_only": True,
        "kdp_setup_screen_is_authoritative": True,
        "sources_checked_at": SOURCE_CHECKED_AT,
        "source_printing_cost": SOURCE_PRINT,
        "source_royalty": SOURCE_ROYALTY,
    }
