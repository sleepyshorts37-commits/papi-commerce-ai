"""KDP full-wrap paperback cover PDF builder using an exact downloaded KDP template."""
from __future__ import annotations

import hashlib
import math
import os
from pathlib import Path
import tempfile
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.utils import ImageReader

from .papi_kids_asset_store import inspect_image
from .papi_kids_kdp_preflight import KDPPreflightError, calculate_kdp_cover_dimensions


class KDPCoverError(ValueError):
    """Cover template, assets, geometry or typography failed preflight."""


def _box(box: Any, label: str) -> tuple[float, float, float, float]:
    if not isinstance(box, dict):
        raise KDPCoverError(f"Zone {label} absente.")
    try:
        values = tuple(float(box[key]) for key in ("x", "y", "width", "height"))
    except (KeyError, TypeError, ValueError) as exc:
        raise KDPCoverError(f"Zone {label} invalide.") from exc
    x, y, width, height = values
    if min(values) < 0 or width <= 0 or height <= 0:
        raise KDPCoverError(f"Dimensions de zone {label} invalides.")
    return values


def _inside(inner: tuple[float, float, float, float], outer: tuple[float, float, float, float]) -> bool:
    x, y, width, height = inner
    ox, oy, ow, oh = outer
    return x >= ox and y >= oy and x + width <= ox + ow and y + height <= oy + oh


def _overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def _verified_cover_image(
    root: Path, record: dict[str, Any], *, panel: tuple[float, float, float, float],
    dpi_target: int, label: str,
) -> Path:
    if not isinstance(record, dict) or record.get("review_status") != "approved":
        raise KDPCoverError(f"Illustration de couverture {label} non approuvée.")
    key = record.get("storage_key", "")
    if not isinstance(key, str) or not key.startswith("covers/") or ".." in Path(key).parts:
        raise KDPCoverError(f"Chemin privé de couverture {label} invalide.")
    path = (root / key).resolve()
    if root not in path.parents or not path.is_file():
        raise KDPCoverError(f"Fichier de couverture {label} absent.")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != record.get("sha256"):
        raise KDPCoverError(f"SHA-256 de la couverture {label} incorrect.")
    width, height = inspect_image(data, record.get("media_type"))
    if (width, height) != (record.get("width_px"), record.get("height_px")):
        raise KDPCoverError(f"Dimensions de la couverture {label} incohérentes.")
    panel_width, panel_height = panel[2], panel[3]
    if width < math.ceil(panel_width * dpi_target) or height < math.ceil(panel_height * dpi_target):
        raise KDPCoverError(f"Résolution de couverture {label} inférieure à {dpi_target} DPI.")
    return path


def build_kdp_cover_pdf(
    storage_root: str | Path,
    output_path: str | Path,
    *,
    trim_width_in: float,
    trim_height_in: float,
    page_count: int,
    paper_type: str,
    cover_template: dict[str, Any],
    front_asset: dict[str, Any],
    back_asset: dict[str, Any],
    title: str,
    author: str,
    back_cover_text: str,
    font_path: str | Path,
    dpi_target: int = 300,
    spine_title: str | None = None,
) -> dict[str, Any]:
    """Compose one-page full-wrap PDF. A verified KDP template is mandatory."""
    if not isinstance(title, str) or not title.strip() or len(title) > 200:
        raise KDPCoverError("Titre de couverture absent ou invalide.")
    if not isinstance(author, str) or not author.strip() or len(author) > 120:
        raise KDPCoverError("Auteur confirmé absent ou invalide.")
    if not isinstance(back_cover_text, str) or not 50 <= len(back_cover_text) <= 1200:
        raise KDPCoverError("Texte de quatrième absent ou hors limites.")
    if not isinstance(dpi_target, int) or not 1 <= dpi_target <= 600:
        raise KDPCoverError("DPI cible invalide.")
    if not isinstance(cover_template, dict):
        raise KDPCoverError("Gabarit KDP officiel manquant.")
    template_path = Path(cover_template.get("template_path", ""))
    if not template_path.is_file():
        raise KDPCoverError("Fichier de gabarit KDP introuvable.")
    template_sha = hashlib.sha256(template_path.read_bytes()).hexdigest()
    if template_sha != cover_template.get("template_sha256"):
        raise KDPCoverError("Empreinte du gabarit KDP incorrecte.")
    if not str(cover_template.get("source_url", "")).startswith("https://kdp.amazon.com/"):
        raise KDPCoverError("La source du gabarit doit être le domaine officiel KDP.")
    if not cover_template.get("downloaded_at"):
        raise KDPCoverError("Date de téléchargement du gabarit manquante.")

    try:
        dimensions = calculate_kdp_cover_dimensions(
            trim_width_in=trim_width_in, trim_height_in=trim_height_in,
            page_count=page_count, paper_type=paper_type,
        )
    except KDPPreflightError as exc:
        raise KDPCoverError(str(exc)) from exc
    page_width = float(cover_template.get("page_width_in", 0))
    page_height = float(cover_template.get("page_height_in", 0))
    if abs(page_width - dimensions["cover_width_in"]) > 0.01 or abs(page_height - dimensions["cover_height_in"]) > 0.01:
        raise KDPCoverError("Dimensions du gabarit incompatibles avec le calcul KDP.")

    back = _box(cover_template.get("back_panel"), "dos de couverture")
    spine = _box(cover_template.get("spine_box"), "dos")
    front = _box(cover_template.get("front_panel"), "première de couverture")
    barcode = _box(cover_template.get("barcode_box"), "code-barres")
    title_box = _box(cover_template.get("title_box"), "titre")
    author_box = _box(cover_template.get("author_box"), "auteur")
    summary_box = _box(cover_template.get("summary_box"), "résumé")
    expected_panel_w = trim_width_in + 0.125
    expected_panel_h = trim_height_in + 0.25
    if any(abs(value - expected_panel_w) > 0.01 for value in (back[2], front[2])):
        raise KDPCoverError("Largeur de panneau incompatible avec le bleed KDP.")
    if any(abs(value - expected_panel_h) > 0.01 for value in (back[3], front[3], spine[3])):
        raise KDPCoverError("Hauteur de panneau incompatible avec le bleed KDP.")
    if abs(back[0]) > 0.01 or abs(back[1]) > 0.01:
        raise KDPCoverError("Le panneau arrière doit commencer à l'origine du gabarit.")
    if abs(spine[0] - (back[0] + back[2])) > 0.01 or abs(spine[2] - dimensions["spine_width_in"]) > 0.01:
        raise KDPCoverError("Position ou largeur du dos incorrecte.")
    if abs(front[0] - (spine[0] + spine[2])) > 0.01 or abs(front[1]) > 0.01:
        raise KDPCoverError("Position du panneau avant incorrecte.")
    if abs(front[0] + front[2] - page_width) > 0.01:
        raise KDPCoverError("Le panneau avant ne rejoint pas le bord du gabarit.")

    # Keep all typography inside the trim-safe area, at least 0.25 in from trim edges.
    safe_back = (0.375, 0.375, trim_width_in - 0.5, trim_height_in - 0.5)
    safe_front = (front[0] + 0.375, 0.375, trim_width_in - 0.5, trim_height_in - 0.5)
    if not all(_inside(item, safe_front) for item in (title_box, author_box)):
        raise KDPCoverError("Titre ou auteur trop proche du bord de coupe.")
    if not _inside(summary_box, safe_back) or not _inside(barcode, safe_back):
        raise KDPCoverError("Résumé ou zone code-barres hors zone sûre de la quatrième.")
    if _overlap(summary_box, barcode):
        raise KDPCoverError("Le résumé empiète sur la zone réservée au code-barres.")
    if page_count <= 79 and spine_title:
        raise KDPCoverError("KDP n'imprime pas de texte sur le dos jusqu'à 79 pages.")
    if not Path(font_path).is_file():
        raise KDPCoverError("Police TrueType à incorporer introuvable.")

    root = Path(storage_root).resolve()
    front_path = _verified_cover_image(root, front_asset, panel=front, dpi_target=dpi_target, label="avant")
    back_path = _verified_cover_image(root, back_asset, panel=back, dpi_target=dpi_target, label="arrière")
    font_name = "PapiKidsCoverEmbedded"
    try:
        pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
    except Exception as exc:
        raise KDPCoverError("Police de couverture impossible à incorporer.") from exc

    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=".papi-cover-", suffix=".pdf", dir=output.parent)
    os.close(fd)
    try:
        pdf = canvas.Canvas(
            temporary_name, pagesize=(page_width * inch, page_height * inch),
            pageCompression=1, invariant=1,
        )
        pdf.setTitle("")
        pdf.setAuthor("")
        pdf.setSubject("")
        pdf.setKeywords("")
        pdf.setCreator("")
        pdf.setProducer("")
        pdf.drawImage(ImageReader(str(back_path)), back[0] * inch, back[1] * inch,
                      width=back[2] * inch, height=back[3] * inch, mask="auto")
        pdf.setFillColor(colors.HexColor("#ffffff"))
        pdf.rect(barcode[0] * inch, barcode[1] * inch,
                 barcode[2] * inch, barcode[3] * inch, stroke=0, fill=1)
        pdf.drawImage(ImageReader(str(front_path)), front[0] * inch, front[1] * inch,
                      width=front[2] * inch, height=front[3] * inch, mask="auto")
        pdf.setFillColor(colors.HexColor("#172033"))
        title_style = ParagraphStyle("CoverTitle", fontName=font_name, fontSize=30, leading=34,
                                     alignment=1, textColor=colors.HexColor("#172033"))
        author_style = ParagraphStyle("CoverAuthor", fontName=font_name, fontSize=16, leading=19,
                                      alignment=1, textColor=colors.HexColor("#172033"))
        summary_style = ParagraphStyle("CoverSummary", fontName=font_name, fontSize=11, leading=15,
                                       alignment=0, textColor=colors.HexColor("#172033"))
        for text, box, style in (
            (title, title_box, title_style),
            (author, author_box, author_style),
            (back_cover_text, summary_box, summary_style),
        ):
            x, y, width, height = box
            paragraph = Paragraph(escape(text).replace("\n", "<br/>"), style)
            wrapped_w, wrapped_h = paragraph.wrap(width * inch, height * inch)
            if wrapped_w > width * inch or wrapped_h > height * inch:
                raise KDPCoverError("Texte trop long pour sa zone de couverture.")
            paragraph.drawOn(pdf, x * inch, y * inch + (height * inch - wrapped_h))
        if spine_title and page_count > 79:
            # Spine text geometry must be explicitly supplied by the verified KDP template.
            spine_text_box = _box(cover_template.get("spine_text_box"), "texte de dos")
            if not _inside(spine_text_box, spine):
                raise KDPCoverError("Texte de dos hors zone du gabarit.")
            pdf.saveState()
            pdf.translate(
                (spine_text_box[0] + spine_text_box[2] / 2) * inch,
                (spine_text_box[1] + spine_text_box[3] / 2) * inch,
            )
            pdf.rotate(90)
            pdf.setFont(font_name, 8)
            pdf.drawCentredString(0, -2, spine_title)
            pdf.restoreState()
        pdf.showPage()
        pdf.save()
        data = Path(temporary_name).read_bytes()
        if not data.startswith(b"%PDF-") or b"/Type /Page" not in data:
            raise KDPCoverError("PDF de couverture invalide.")
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, output)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return {
        "output_path": str(output),
        "page_count": 1,
        "page_width_in": page_width,
        "page_height_in": page_height,
        "spine_width_in": dimensions["spine_width_in"],
        "template_sha256": template_sha,
        "font_embedded": True,
        "barcode_reserved": True,
        "human_approval_required": True,
        "kdp_submission_ready": False,
    }
