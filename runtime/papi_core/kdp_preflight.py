"""Calculs géométriques et contrôles préliminaires selon l'aide officielle KDP."""
from __future__ import annotations

from dataclasses import asdict, dataclass


class KdpPreflightError(ValueError):
    """Paramètres d'impression incompatibles avec les règles prises en charge."""


SPINE_COEFFICIENTS_IN = {
    "white": 0.002252,
    "cream": 0.0025,
    "groundwood": 0.00235,
    "premium_color": 0.002347,
    "standard_color": 0.002252,
}


@dataclass(frozen=True)
class CoverDimensions:
    trim_width_in: float
    trim_height_in: float
    page_count: int
    paper_type: str
    bleed_in: float
    spine_width_in: float
    full_cover_width_in: float
    full_cover_height_in: float
    spine_text_allowed: bool
    calculation_basis: str = "Amazon KDP paperback cover help; verify again in KDP Cover Calculator"


def calculate_paperback_cover(
    trim_width_in: float,
    trim_height_in: float,
    page_count: int,
    paper_type: str,
) -> CoverDimensions:
    """Calcule le gabarit pleine couverture, avec fond perdu KDP de 0.125 po."""
    if not isinstance(trim_width_in, (int, float)) or not 4.0 <= trim_width_in <= 8.5:
        raise KdpPreflightError("Largeur de coupe hors limites prises en charge.")
    if not isinstance(trim_height_in, (int, float)) or not 6.0 <= trim_height_in <= 11.69:
        raise KdpPreflightError("Hauteur de coupe hors limites prises en charge.")
    if not isinstance(page_count, int) or not 24 <= page_count <= 828:
        raise KdpPreflightError("Pagination hors plage générale KDP prise en charge.")
    if paper_type not in SPINE_COEFFICIENTS_IN:
        raise KdpPreflightError("Type de papier inconnu.")
    bleed = 0.125
    spine = page_count * SPINE_COEFFICIENTS_IN[paper_type]
    return CoverDimensions(
        trim_width_in=float(trim_width_in),
        trim_height_in=float(trim_height_in),
        page_count=page_count,
        paper_type=paper_type,
        bleed_in=bleed,
        spine_width_in=round(spine, 5),
        full_cover_width_in=round(2 * trim_width_in + spine + 2 * bleed, 5),
        full_cover_height_in=round(trim_height_in + 2 * bleed, 5),
        spine_text_allowed=page_count >= 80,
    )


def paperback_minimum_margins(page_count: int, *, bleed: bool = False) -> dict[str, float]:
    """Retourne les marges minimales KDP en pouces selon la pagination."""
    if not isinstance(page_count, int) or not 24 <= page_count <= 828:
        raise KdpPreflightError("La pagination doit être comprise entre 24 et 828 pages.")
    if page_count <= 150:
        gutter = 0.375
    elif page_count <= 300:
        gutter = 0.5
    elif page_count <= 500:
        gutter = 0.625
    elif page_count <= 700:
        gutter = 0.75
    else:
        gutter = 0.875
    outside = 0.375 if bleed else 0.25
    return {
        "inside_gutter_in": gutter,
        "outside_min_in": outside,
        "top_min_in": outside,
        "bottom_min_in": outside,
        "interior_bleed_extension_in": 0.125 if bleed else 0.0,
    }


def cover_dimensions_dict(spec: CoverDimensions) -> dict:
    return asdict(spec)
