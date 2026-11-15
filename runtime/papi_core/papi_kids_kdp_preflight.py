"""KDP paperback preflight and print-ready interior PDF builder for PAPI KIDS."""
from __future__ import annotations

import hashlib
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.utils import ImageReader

from .papi_kids_asset_store import inspect_image

# Current official KDP paperback color page limits verified 2026-11-15.
# Only trim sizes with explicit entries below are accepted by this preflight.
KDP_COLOR_PAGE_LIMITS = {
    (5.00, 8.00): {"standard_color": (72, 600), "premium_color": (24, 828)},
    (5.50, 8.50): {"standard_color": (72, 600), "premium_color": (24, 828)},
    (6.00, 9.00): {"standard_color": (72, 600), "premium_color": (24, 828)},
    (7.00, 10.00): {"standard_color": (72, 600), "premium_color": (24, 828)},
    (7.50, 9.25): {"standard_color": (72, 600), "premium_color": (24, 828)},
    (8.25, 8.25): {"standard_color": (72, 600), "premium_color": (24, 800)},
    (8.50, 8.50): {"standard_color": (72, 600), "premium_color": (24, 590)},
    (8.50, 11.00): {"standard_color": (72, 600), "premium_color": (24, 590)},
}
_UPLOAD_ID = re.compile(r"^PKP-UP-[0-9a-f]{32}$")


class KDPPreflightError(ValueError):
    """The proposed interior or cover geometry fails KDP preflight."""


def validate_kdp_spec(
    *,
    trim_width_in: float,
    trim_height_in: float,
    page_count: int,
    color_mode: str,
    bleed: bool,
    inside_margin_in: float,
    outside_margin_in: float,
    top_margin_in: float,
    bottom_margin_in: float,
) -> dict[str, Any]:
    """Validate a color paperback profile against the supported official KDP table."""
    if color_mode not in {"standard_color", "premium_color"}:
        raise KDPPreflightError("Mode couleur KDP non pris en charge par ce profil.")
    if not isinstance(page_count, int) or isinstance(page_count, bool) or page_count % 2 or page_count < 24:
        raise KDPPreflightError("La pagination doit être paire et compter au moins 24 pages.")
    size = (round(float(trim_width_in), 2), round(float(trim_height_in), 2))
    limits = KDP_COLOR_PAGE_LIMITS.get(size, {}).get(color_mode)
    if limits is None:
        raise KDPPreflightError("Format de coupe non présent dans la table KDP vérifiée.")
    minimum_pages, maximum_pages = limits
    if not minimum_pages <= page_count <= maximum_pages:
        raise KDPPreflightError(
            f"Pagination hors limites KDP pour {color_mode}: {minimum_pages} à {maximum_pages} pages."
        )
    if page_count <= 150:
        required_inside = 0.375
    elif page_count <= 300:
        required_inside = 0.5
    elif page_count <= 500:
        required_inside = 0.625
    elif page_count <= 700:
        required_inside = 0.75
    else:
        required_inside = 0.875
    required_outside = 0.375 if bleed else 0.25
    if inside_margin_in < required_inside:
        raise KDPPreflightError(f"Gouttière minimale KDP : {required_inside:.3f} po.")
    if outside_margin_in < required_outside:
        raise KDPPreflightError(f"Marge extérieure minimale KDP : {required_outside:.3f} po.")
    if min(top_margin_in, bottom_margin_in) < required_outside:
        raise KDPPreflightError(f"Marges haut/bas minimales : {required_outside:.3f} po.")
    bleed_width = 0.125 if bleed else 0.0
    bleed_height = 0.25 if bleed else 0.0
    return {
        "trim_width_in": size[0],
        "trim_height_in": size[1],
        "page_count": page_count,
        "color_mode": color_mode,
        "bleed": bool(bleed),
        "pdf_width_in": size[0] + bleed_width,
        "pdf_height_in": size[1] + bleed_height,
        "required_inside_margin_in": required_inside,
        "required_outside_margin_in": required_outside,
        "minimum_image_dpi": 300,
        "source_verified_at": "2026-11-15",
        "source_url": "https://kdp.amazon.com/help/topic/G201857950",
    }


def calculate_kdp_cover_dimensions(
    *, trim_width_in: float, trim_height_in: float, page_count: int, paper_type: str = "color"
) -> dict[str, Any]:
    """Calculate full-wrap cover dimensions; KDP cover template remains authoritative."""
    if not isinstance(page_count, int) or isinstance(page_count, bool) or page_count < 24 or page_count % 2:
        raise KDPPreflightError("Pagination de couverture invalide.")
    if paper_type != "color":
        raise KDPPreflightError("Seul le coefficient papier couleur est configuré.")
    spine = page_count * 0.002347
    bleed = 0.125
    return {
        "spine_width_in": round(spine, 6),
        "cover_width_in": round(2 * trim_width_in + spine + 2 * bleed, 6),
        "cover_height_in": round(trim_height_in + 2 * bleed, 6),
        "bleed_in": bleed,
        "spine_text_allowed": page_count > 79,
        "template_required_before_export": True,
        "source_url": "https://kdp.amazon.com/help/topic/G201857950",
    }


def build_interior_pdf(
    storage_root: str | Path,
    output_path: str | Path,
    *,
    upload_id: str,
    assets: list[dict[str, Any]],
    pages: list[dict[str, Any]],
    font_path: str | Path,
    trim_width_in: float,
    trim_height_in: float,
    color_mode: str,
    bleed: bool,
    inside_margin_in: float,
    outside_margin_in: float,
    top_margin_in: float,
    bottom_margin_in: float,
    dpi_target: int = 300,
) -> dict[str, Any]:
    """Build a single-page-per-sheet PDF only from approved, high-resolution assets."""
    if not isinstance(upload_id, str) or not _UPLOAD_ID.fullmatch(upload_id):
        raise KDPPreflightError("Référence de dépôt invalide.")
    if not isinstance(dpi_target, int) or dpi_target < 1 or dpi_target > 600:
        raise KDPPreflightError("DPI cible invalide.")
    if not isinstance(assets, list) or not isinstance(pages, list) or len(assets) != len(pages):
        raise KDPPreflightError("Chaque page doit avoir une illustration et un bloc texte.")
    page_count = len(pages)
    spec = validate_kdp_spec(
        trim_width_in=trim_width_in, trim_height_in=trim_height_in,
        page_count=page_count, color_mode=color_mode, bleed=bleed,
        inside_margin_in=inside_margin_in, outside_margin_in=outside_margin_in,
        top_margin_in=top_margin_in, bottom_margin_in=bottom_margin_in,
    )
    if not Path(font_path).is_file():
        raise KDPPreflightError("Police TrueType à incorporer introuvable.")
    font_name = "PapiKidsEmbedded"
    try:
        pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
    except Exception as exc:
        raise KDPPreflightError("Impossible d'incorporer la police fournie.") from exc

    by_page: dict[int, dict[str, Any]] = {}
    for asset in assets:
        if not isinstance(asset, dict):
            raise KDPPreflightError("Métadonnée d'illustration invalide.")
        number = asset.get("page_number")
        if not isinstance(number, int) or number in by_page:
            raise KDPPreflightError("Pages d'illustration dupliquées ou invalides.")
        if asset.get("review_status") != "approved":
            raise KDPPreflightError(f"L'illustration de la page {number} n'est pas approuvée.")
        by_page[number] = asset
    if sorted(by_page) != list(range(1, page_count + 1)):
        raise KDPPreflightError("Une illustration approuvée est requise pour chaque page.")

    root = Path(storage_root).resolve()
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_fd, temp_name = tempfile.mkstemp(prefix=".papi-kdp-", suffix=".pdf", dir=output.parent)
    os.close(temp_fd)
    trim_w = trim_width_in * inch
    trim_h = trim_height_in * inch
    pdf_w = spec["pdf_width_in"] * inch
    pdf_h = spec["pdf_height_in"] * inch
    style = ParagraphStyle(
        "PapiKidsBody", fontName=font_name, fontSize=16, leading=21,
        textColor="#111111", spaceAfter=0, allowWidows=0, allowOrphans=0,
    )
    try:
        pdf = canvas.Canvas(temp_name, pagesize=(pdf_w, pdf_h), pageCompression=1, invariant=1)
        pdf.setTitle("")
        pdf.setAuthor("")
        pdf.setSubject("")
        pdf.setKeywords("")
        pdf.setCreator("")
        pdf.setProducer("")
        pdf.setPageCompression(1)
        for number, page in enumerate(pages, start=1):
            if not isinstance(page, dict) or page.get("page_number") != number:
                raise KDPPreflightError("Pages texte manquantes ou désordonnées.")
            asset = by_page[number]
            key = asset.get("storage_key", "")
            prefix = f"{upload_id}/illustrations/"
            if not isinstance(key, str) or not key.startswith(prefix) or ".." in Path(key).parts:
                raise KDPPreflightError("Clé de stockage d'illustration invalide.")
            image_path = (root / key).resolve()
            if root not in image_path.parents or not image_path.is_file():
                raise KDPPreflightError(f"Fichier image privé absent pour la page {number}.")
            image_bytes = image_path.read_bytes()
            media_type = asset.get("media_type")
            width_px, height_px = inspect_image(image_bytes, media_type)
            if (width_px, height_px) != (asset.get("width_px"), asset.get("height_px")):
                raise KDPPreflightError(f"Dimensions enregistrées incohérentes page {number}.")
            digest = hashlib.sha256(image_bytes).hexdigest()
            if digest != asset.get("sha256"):
                raise KDPPreflightError(f"Empreinte SHA-256 incohérente page {number}.")
            required_width = math.ceil(spec["pdf_width_in"] * dpi_target)
            required_height = math.ceil(spec["pdf_height_in"] * dpi_target)
            if width_px < required_width or height_px < required_height:
                raise KDPPreflightError(
                    f"Page {number}: {width_px}×{height_px}px, minimum {required_width}×{required_height}px."
                )
            pdf.drawImage(ImageReader(str(image_path)), 0, 0, width=pdf_w, height=pdf_h, mask="auto")

            text = page.get("text", "")
            box = page.get("text_box")
            if not isinstance(text, str) or not isinstance(box, dict):
                raise KDPPreflightError(f"Bloc texte ou position manquant page {number}.")
            x, y, width, height = (float(box.get(k, 0)) for k in ("x", "y", "width", "height"))
            if min(x, y, width, height) < 0 or width <= 0 or height <= 0:
                raise KDPPreflightError(f"Boîte texte invalide page {number}.")
            page_left_inside = number % 2 == 0
            min_x = outside_margin_in if page_left_inside else inside_margin_in
            max_right = trim_width_in - (inside_margin_in if page_left_inside else outside_margin_in)
            if x < min_x or x + width > max_right:
                raise KDPPreflightError(f"Bloc texte hors marges horizontales page {number}.")
            if y < bottom_margin_in or y + height > trim_height_in - top_margin_in:
                raise KDPPreflightError(f"Bloc texte hors marges verticales page {number}.")
            bleed_x = 0.125 * inch if bleed and page_left_inside else 0
            paragraph = Paragraph(escape(text).replace("\n", "<br/>"), style)
            wrapped_w, wrapped_h = paragraph.wrap(width * inch, height * inch)
            if wrapped_w > width * inch or wrapped_h > height * inch:
                raise KDPPreflightError(f"Texte trop long pour sa zone page {number}.")
            paragraph.drawOn(pdf, bleed_x + x * inch, y * inch + (height * inch - wrapped_h))
            pdf.showPage()
        pdf.save()
        data = Path(temp_name).read_bytes()
        if not data.startswith(b"%PDF-") or len(data) > 650 * 1024 * 1024:
            raise KDPPreflightError("PDF produit invalide ou supérieur à 650 Mio.")
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, output)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
    return {
        "output_path": str(output),
        "page_count": page_count,
        "pdf_width_in": spec["pdf_width_in"],
        "pdf_height_in": spec["pdf_height_in"],
        "font_embedded": True,
        "image_dpi_target": dpi_target,
        "human_approval_required": True,
        "kdp_submission_ready": False,
        "preflight": "structural_pdf_generated_not_yet_manually_inspected",
    }
