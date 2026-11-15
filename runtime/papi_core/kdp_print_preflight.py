"""Fail-closed KDP print preflight manifest validation.

This validates measurements produced by a PDF/image inspector against a current,
operator-supplied official KDP template. It does not pretend to parse PDFs itself.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse


class KDPPreflightError(ValueError):
    """Missing or non-compliant KDP print-production evidence."""


MAX_TEMPLATE_AGE = timedelta(days=30)


def _positive_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise KDPPreflightError(f"Mesure {field} invalide.")
    return float(value)


def validate_kdp_preflight_manifest(
    *,
    template: dict[str, Any],
    manifest: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Compare actual PDF inspection measurements with the official KDP template."""
    if not isinstance(template, dict) or not isinstance(manifest, dict):
        raise KDPPreflightError("Gabarit officiel et manifeste d'inspection obligatoires.")
    required_template = (
        "source_url", "template_ref", "retrieved_at", "trim_width_in",
        "trim_height_in", "page_count", "bleed", "minimum_dpi",
        "minimum_inner_margin_in", "minimum_outer_margin_in",
        "minimum_top_margin_in", "minimum_bottom_margin_in",
        "minimum_gutter_in",
    )
    if any(key not in template for key in required_template):
        raise KDPPreflightError("Gabarit KDP incomplet : aucune dimension ne sera devinée.")
    url = urlparse(template["source_url"]) if isinstance(template["source_url"], str) else None
    if url is None or url.scheme != "https" or url.hostname not in {"kdp.amazon.com"}:
        raise KDPPreflightError("Le gabarit doit provenir du domaine officiel kdp.amazon.com.")
    if not isinstance(template["template_ref"], str) or not template["template_ref"].strip():
        raise KDPPreflightError("Référence du gabarit officiel absente.")
    retrieved = template["retrieved_at"]
    if not isinstance(retrieved, str):
        raise KDPPreflightError("Date de récupération du gabarit absente.")
    try:
        stamp = datetime.fromisoformat(retrieved.replace("Z", "+00:00"))
    except ValueError as exc:
        raise KDPPreflightError("Date du gabarit invalide.") from exc
    if stamp.tzinfo is None:
        raise KDPPreflightError("Date du gabarit sans fuseau horaire.")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise KDPPreflightError("Horloge sans fuseau horaire.")
    if stamp > current or current - stamp.astimezone(timezone.utc) > MAX_TEMPLATE_AGE:
        raise KDPPreflightError("Gabarit KDP trop ancien : actualisation requise (30 jours maximum).")

    expected_width = _positive_number(template["trim_width_in"], "trim_width_in")
    expected_height = _positive_number(template["trim_height_in"], "trim_height_in")
    if not isinstance(template["page_count"], int) or isinstance(template["page_count"], bool) or template["page_count"] < 24:
        raise KDPPreflightError("Pagination imprimée invalide ou inférieure au contenu du livre.")
    if template["bleed"] not in {"bleed", "no_bleed"}:
        raise KDPPreflightError("Type de fond perdu non reconnu.")
    min_dpi = template["minimum_dpi"]
    if not isinstance(min_dpi, int) or isinstance(min_dpi, bool) or min_dpi < 72:
        raise KDPPreflightError("Résolution minimale du gabarit invalide.")

    required_manifest = (
        "interior_pdf", "cover_pdf", "interior_page_count",
        "interior_page_width_in", "interior_page_height_in",
        "cover_width_in", "cover_height_in", "fonts_embedded",
        "page_order_valid", "blank_pages_reviewed", "images",
        "minimum_inner_margin_in", "minimum_outer_margin_in",
        "minimum_top_margin_in", "minimum_bottom_margin_in",
        "minimum_gutter_in", "pdf_preflight_completed",
    )
    if any(key not in manifest for key in required_manifest):
        raise KDPPreflightError("Manifeste PDF incomplet : préflight non démontré.")
    blockers = []
    if manifest["interior_page_count"] != template["page_count"]:
        blockers.append("interior_page_count_mismatch")
    for field, expected in (
        ("interior_page_width_in", expected_width),
        ("interior_page_height_in", expected_height),
    ):
        actual = _positive_number(manifest[field], field)
        if abs(actual - expected) > 0.01:
            blockers.append(f"{field}_mismatch")
    _positive_number(manifest["cover_width_in"], "cover_width_in")
    _positive_number(manifest["cover_height_in"], "cover_height_in")
    for field in (
        "minimum_inner_margin_in", "minimum_outer_margin_in",
        "minimum_top_margin_in", "minimum_bottom_margin_in",
        "minimum_gutter_in",
    ):
        actual = _positive_number(manifest[field], field)
        expected = _positive_number(template[field], field)
        if actual + 1e-6 < expected:
            blockers.append(f"{field}_below_kdp_minimum")
    if manifest["fonts_embedded"] is not True:
        blockers.append("fonts_not_embedded")
    if manifest["page_order_valid"] is not True:
        blockers.append("page_order_invalid")
    if manifest["blank_pages_reviewed"] is not True:
        blockers.append("blank_pages_not_reviewed")
    if manifest["pdf_preflight_completed"] is not True:
        blockers.append("pdf_preflight_not_completed")
    images = manifest["images"]
    if not isinstance(images, list) or len(images) != 24:
        blockers.append("expected_24_page_images")
        images = images if isinstance(images, list) else []
    for index, item in enumerate(images):
        if not isinstance(item, dict):
            blockers.append(f"image_{index + 1}_manifest_invalid")
            continue
        width = item.get("pixel_width")
        height = item.get("pixel_height")
        dpi = item.get("effective_dpi")
        if any(not isinstance(v, int) or isinstance(v, bool) or v <= 0 for v in (width, height)):
            blockers.append(f"image_{index + 1}_dimensions_invalid")
        if not isinstance(dpi, (int, float)) or isinstance(dpi, bool) or dpi < min_dpi:
            blockers.append(f"image_{index + 1}_resolution_below_minimum")
        if item.get("sha256") is None or not isinstance(item.get("sha256"), str) or len(item["sha256"]) != 64:
            blockers.append(f"image_{index + 1}_sha256_missing")
    return {
        "status": "ready_for_human_review" if not blockers else "blocked",
        "book_id": "PKP-0001",
        "template_ref": template["template_ref"],
        "template_retrieved_at": stamp.astimezone(timezone.utc).isoformat(),
        "blockers": blockers,
        "human_approval_required": True,
        "kdp_upload_authorized": False,
    }
