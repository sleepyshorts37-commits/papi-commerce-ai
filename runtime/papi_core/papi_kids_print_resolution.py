"""Auditable KDP image resolution and super-resolution review gate."""
from __future__ import annotations

import math
import re
from typing import Any


class PrintResolutionError(ValueError):
    """Image dimensions or resolution evidence is invalid."""


def audit_image_resolution(
    *,
    source_width_px: int,
    source_height_px: int,
    final_width_px: int,
    final_height_px: int,
    trim_width_in: float,
    trim_height_in: float,
    bleed: bool,
    output_sha256: str,
    upscaling_method: str = "native",
    resolution_review: dict[str, Any] | None = None,
    target_dpi: int = 300,
) -> dict[str, Any]:
    """Separate source-detail DPI from final pixel DPI; never bless Lanczos as AI detail."""
    dimensions = (source_width_px, source_height_px, final_width_px, final_height_px, target_dpi)
    if any(not isinstance(v, int) or isinstance(v, bool) or v <= 0 for v in dimensions):
        raise PrintResolutionError("Dimensions ou DPI invalides.")
    if not re.fullmatch(r"[0-9a-f]{64}", output_sha256):
        raise PrintResolutionError("SHA-256 de sortie invalide.")
    if upscaling_method not in {"native", "ai_super_resolution", "manual_retouch", "lanczos_only"}:
        raise PrintResolutionError("Méthode de résolution inconnue.")
    pdf_width = float(trim_width_in) + (0.125 if bleed else 0)
    pdf_height = float(trim_height_in) + (0.25 if bleed else 0)
    if pdf_width <= 0 or pdf_height <= 0:
        raise PrintResolutionError("Format imprimé invalide.")
    source_dpi_x = source_width_px / pdf_width
    source_dpi_y = source_height_px / pdf_height
    final_dpi_x = final_width_px / pdf_width
    final_dpi_y = final_height_px / pdf_height
    source_dpi = round(min(source_dpi_x, source_dpi_y), 2)
    final_dpi = round(min(final_dpi_x, final_dpi_y), 2)
    required_width = math.ceil(pdf_width * target_dpi)
    required_height = math.ceil(pdf_height * target_dpi)
    final_pixels_pass = final_width_px >= required_width and final_height_px >= required_height
    native_detail_pass = source_dpi >= target_dpi
    review = resolution_review or {}
    reviewed_upscale = (
        upscaling_method in {"ai_super_resolution", "manual_retouch"}
        and review.get("approved") is True
        and bool(review.get("reviewer_id"))
        and bool(review.get("approved_at"))
        and review.get("output_sha256") == output_sha256
    )
    print_ready = final_pixels_pass and (native_detail_pass or reviewed_upscale)
    if upscaling_method == "lanczos_only" and not native_detail_pass:
        print_ready = False
    return {
        "source_dpi": source_dpi,
        "final_pixel_dpi": final_dpi,
        "required_width_px": required_width,
        "required_height_px": required_height,
        "source_detail_pass": native_detail_pass,
        "final_pixel_pass": final_pixels_pass,
        "upscale_review_pass": reviewed_upscale,
        "upscaling_method": upscaling_method,
        "print_ready": print_ready,
        "status": "print_ready" if print_ready else "high_resolution_review_required",
        "output_sha256": output_sha256,
        "target_dpi": target_dpi,
    }


def audit_illustration_campaign(
    assets: list[dict[str, Any]],
    *,
    page_count: int,
    trim_width_in: float,
    trim_height_in: float,
    bleed: bool,
) -> dict[str, Any]:
    if not isinstance(assets, list) or not isinstance(page_count, int) or page_count < 1:
        raise PrintResolutionError("Campagne d'illustrations invalide.")
    by_page = {}
    results = []
    for asset in assets:
        if not isinstance(asset, dict):
            raise PrintResolutionError("Métadonnée image invalide.")
        number = asset.get("page_number")
        if not isinstance(number, int) or number in by_page or not 1 <= number <= page_count:
            raise PrintResolutionError("Numéro de page dupliqué ou invalide.")
        by_page[number] = asset
        result = audit_image_resolution(
            source_width_px=asset["source_width_px"],
            source_height_px=asset["source_height_px"],
            final_width_px=asset["width_px"],
            final_height_px=asset["height_px"],
            trim_width_in=trim_width_in,
            trim_height_in=trim_height_in,
            bleed=bleed,
            output_sha256=asset["sha256"],
            upscaling_method=asset.get("upscaling_method", "native"),
            resolution_review=asset.get("resolution_review"),
        )
        result["page_number"] = number
        results.append(result)
    missing = sorted(set(range(1, page_count + 1)) - set(by_page))
    blocked = [item["page_number"] for item in results if not item["print_ready"]]
    return {
        "page_count": page_count,
        "missing_pages": missing,
        "blocked_pages": blocked,
        "ready_pages": page_count - len(missing) - len(blocked),
        "print_ready": not missing and not blocked,
        "results": sorted(results, key=lambda item: item["page_number"]),
    }
