"""Amazon KDP full-wrap cover PDF builder bound to a verified template file."""
from __future__ import annotations

import hashlib
import math
import os
from pathlib import Path
from xml.sax.saxutils import escape
import re
import tempfile
from typing import Any

from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.utils import ImageReader

from .papi_kids_asset_store import inspect_image

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UPLOAD_ID = re.compile(r"^PKP-UP-[0-9a-f]{32}$")


class KDPCoverError(ValueError):
    """Cover template, art or geometry failed preflight."""


def _rect(value: Any, name: str, page_w: float, page_h: float) -> tuple[float, float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise KDPCoverError(f"Rectangle {name} invalide.")
    x_in, y_in, width_in, height_in = (float(item) for item in value)
    if not all(math.isfinite(item) for item in (x_in, y_in, width_in, height_in)):
        raise KDPCoverError(f"Coordonnées {name} non finies.")
    x, y, width, height = (item * inch for item in (x_in, y_in, width_in, height_in))
    if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > page_w or y + height > page_h:
        raise KDPCoverError(f"Rectangle {name} hors du gabarit.")
    return x, y, width, height


def _image(storage_root: Path, upload_id: str, asset: dict[str, Any], target_rect: tuple[float, float, float, float], dpi: int) -> Path:
    if not isinstance(asset, dict) or asset.get("review_status") != "approved":
        raise KDPCoverError("Les illustrations de couverture doivent être approuvées par un humain.")
    key = asset.get("storage_key", "")
    prefix = f"{upload_id}/covers/"
    if not isinstance(key, str) or not key.startswith(prefix) or ".." in Path(key).parts:
        raise KDPCoverError("Clé de stockage de couverture invalide.")
    path = (storage_root / key).resolve()
    if storage_root not in path.parents or not path.is_file():
        raise KDPCoverError("Illustration de couverture privée introuvable.")
    data = path.read_bytes()
    width, height = inspect_image(data, asset.get("media_type", ""))
    if (width, height) != (asset.get("width_px"), asset.get("height_px")):
        raise KDPCoverError("Dimensions d'illustration incohérentes.")
    if hashlib.sha256(data).hexdigest() != asset.get("sha256"):
        raise KDPCoverError("Empreinte SHA-256 de couverture incorrecte.")
    _, _, target_w, target_h = target_rect
    if width < math.ceil(target_w / inch * dpi) or height < math.ceil(target_h / inch * dpi):
        raise KDPCoverError(f"Image de couverture sous le seuil {dpi} DPI.")
    return path


def build_kdp_full_wrap_cover_pdf(
    storage_root: str | Path,
    output_path: str | Path,
    *,
    upload_id: str,
    template_pdf_path: str | Path,
    template_sha256: str,
    template_layout: dict[str, Any],
    back_art: dict[str, Any],
    front_art: dict[str, Any],
    title: str,
    author: str,
    blurb: str,
    font_path: str | Path,
    page_count: int,
    dpi_target: int = 300,
) -> dict[str, Any]:
    """Render a one-page full-wrap PDF using dimensions measured from the exact KDP template."""
    if not isinstance(upload_id, str) or not _UPLOAD_ID.fullmatch(upload_id):
        raise KDPCoverError("Référence de dépôt invalide.")
    if not isinstance(template_sha256, str) or not _SHA256.fullmatch(template_sha256):
        raise KDPCoverError("Empreinte du gabarit KDP invalide.")
    template_path = Path(template_pdf_path).resolve()
    if not template_path.is_file():
        raise KDPCoverError("Gabarit PDF officiel KDP absent.")
    template_bytes = template_path.read_bytes()
    if not template_bytes.startswith(b"%PDF-") or hashlib.sha256(template_bytes).hexdigest() != template_sha256:
        raise KDPCoverError("Le gabarit PDF ne correspond pas à son empreinte SHA-256.")
    if not isinstance(template_layout, dict) or template_layout.get("source_template_sha256") != template_sha256:
        raise KDPCoverError("La géométrie fournie n'est pas liée au gabarit KDP vérifié.")
    if not isinstance(page_count, int) or isinstance(page_count, bool) or page_count < 24:
        raise KDPCoverError("Pagination du livre invalide.")
    if not isinstance(dpi_target, int) or not 1 <= dpi_target <= 600:
        raise KDPCoverError("DPI cible invalide.")
    if not all(isinstance(value, str) and value.strip() for value in (title, author, blurb)):
        raise KDPCoverError("Titre, auteur et résumé doivent être renseignés et validés.")
    if len(title) > 180 or len(author) > 120 or len(blurb) > 1200:
        raise KDPCoverError("Texte de couverture trop long.")
    if not Path(font_path).is_file():
        raise KDPCoverError("Police TrueType de couverture introuvable.")

    width_in = float(template_layout.get("page_width_in", 0))
    height_in = float(template_layout.get("page_height_in", 0))
    if not (0 < width_in < 30 and 0 < height_in < 30):
        raise KDPCoverError("Dimensions du gabarit hors limites.")
    page_w, page_h = width_in * inch, height_in * inch
    panels = template_layout.get("panels", {})
    back = _rect(panels.get("back"), "back", page_w, page_h)
    front = _rect(panels.get("front"), "front", page_w, page_h)
    spine = _rect(panels.get("spine"), "spine", page_w, page_h)
    barcode = _rect(panels.get("barcode"), "barcode", page_w, page_h)
    bleed = float(template_layout.get("bleed_in", -1))
    if abs(bleed - 0.125) > 0.001:
        raise KDPCoverError("Le gabarit doit contenir le fond perdu KDP de 0,125 po.")
    if back[0] + back[2] > spine[0] + 0.01 or spine[0] + spine[2] > front[0] + 0.01:
        raise KDPCoverError("Ordre géométrique dos/pliure/face avant invalide.")
    if barcode[0] < back[0] or barcode[1] < back[1] or barcode[0] + barcode[2] > back[0] + back[2] or barcode[1] + barcode[3] > back[1] + back[3]:
        raise KDPCoverError("Zone code-barres doit être intégralement sur la quatrième.")
    back_path = _image(Path(storage_root).resolve(), upload_id, back_art, back, dpi_target)
    front_path = _image(Path(storage_root).resolve(), upload_id, front_art, front, dpi_target)
    font_name = "PapiKidsCoverEmbedded"
    try:
        pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
    except Exception as exc:
        raise KDPCoverError("Police de couverture impossible à incorporer.") from exc

    root = Path(storage_root).resolve()
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".papi-cover-", suffix=".pdf", dir=output.parent)
    os.close(fd)
    try:
        pdf = canvas.Canvas(temporary, pagesize=(page_w, page_h), pageCompression=1, invariant=1)
        pdf.setTitle("")
        pdf.setAuthor("")
        pdf.setSubject("")
        pdf.setCreator("")
        pdf.drawImage(ImageReader(str(back_path)), back[0], back[1], back[2], back[3], mask="auto")
        pdf.drawImage(ImageReader(str(front_path)), front[0], front[1], front[2], front[3], mask="auto")

        # Keep the barcode area empty and opaque white for Amazon's barcode placement.
        pdf.setFillColor(white)
        pdf.rect(*barcode, stroke=0, fill=1)

        # Text positions are supplied by the exact-template layout and must stay on the front/back.
        title_box = _rect(template_layout.get("title_box"), "title_box", page_w, page_h)
        author_box = _rect(template_layout.get("author_box"), "author_box", page_w, page_h)
        blurb_box = _rect(template_layout.get("blurb_box"), "blurb_box", page_w, page_h)
        for name, box, panel in (
            ("title", title_box, front), ("author", author_box, front), ("blurb", blurb_box, back)
        ):
            if box[0] < panel[0] or box[1] < panel[1] or box[0] + box[2] > panel[0] + panel[2] or box[1] + box[3] > panel[1] + panel[3]:
                raise KDPCoverError(f"Zone texte {name} hors de son panneau.")
        if page_count < 80 and template_layout.get("spine_text_box") is not None:
            raise KDPCoverError("Le texte sur le dos est interdit pour moins de 80 pages.")
        if page_count >= 80 and template_layout.get("spine_text_box") is not None:
            _rect(template_layout["spine_text_box"], "spine_text_box", page_w, page_h)
            raise KDPCoverError("Le texte sur le dos nécessite un gabarit validé et un traitement typographique distinct.")

        def draw_text(text: str, box: tuple[float, float, float, float], size: float, leading: float) -> None:
            x, y, width, height = box
            style = ParagraphStyle(
                "PapiKidsCoverText", fontName=font_name, fontSize=size,
                leading=leading, textColor=HexColor("#111111"),
                spaceAfter=0, spaceBefore=0,
            )
            paragraph = Paragraph(escape(text).replace("\n", "<br/>"), style)
            _, used_height = paragraph.wrap(width, height)
            if used_height > height:
                raise KDPCoverError("Le texte ne tient pas dans sa zone de couverture.")
            paragraph.drawOn(pdf, x, y + height - used_height)

        draw_text(title, title_box, 28, 34)
        draw_text(author, author_box, 14, 18)
        draw_text(blurb, blurb_box, 11, 14)
        pdf.showPage()
        pdf.save()
        data = Path(temporary).read_bytes()
        if not data.startswith(b"%PDF-") or len(data) > 650 * 1024 * 1024:
            raise KDPCoverError("PDF de couverture invalide ou trop volumineux.")
        os.chmod(temporary, 0o600)
        os.replace(temporary, output)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return {
        "output_path": str(output),
        "page_count": 1,
        "template_sha256": template_sha256,
        "cover_width_in": width_in,
        "cover_height_in": height_in,
        "barcode_zone_left_blank": True,
        "font_embedded": True,
        "image_dpi_target": dpi_target,
        "human_approval_required": True,
        "kdp_submission_ready": False,
        "preflight": "structural_pdf_generated_not_yet_manually_inspected",
    }
