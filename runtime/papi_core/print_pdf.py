"""Génération d'une épreuve PDF intérieure depuis un manuscrit validé."""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import inch
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch as inch_unit
from reportlab.platypus import (
    PageBreak, Paragraph, SimpleDocTemplate, Spacer,
)

from .manuscript import validate_manuscript


class PrintPdfError(ValueError):
    """Configuration d'impression ou génération PDF invalide."""


@dataclass(frozen=True)
class PrintLayout:
    width_in: float = 8.5
    height_in: float = 8.5
    margin_in: float = 0.55
    gutter_in: float = 0.65
    page_count_estimate: int = 24

    def validate(self) -> None:
        if not (4.0 <= self.width_in <= 8.5 and 6.0 <= self.height_in <= 11.69):
            raise PrintPdfError("Format de coupe hors des limites prises en charge.")
        if not (0.25 <= self.margin_in <= 1.5 and 0.25 <= self.gutter_in <= 2.0):
            raise PrintPdfError("Marges ou gouttière hors limites.")
        if not isinstance(self.page_count_estimate, int) or not 1 <= self.page_count_estimate <= 800:
            raise PrintPdfError("Estimation du nombre de pages invalide.")


def build_print_interior_pdf(manuscript: dict[str, Any], layout: PrintLayout | None = None) -> bytes:
    """Produit une épreuve intérieure PDF texte ; couverture et illustrations non incluses."""
    report = validate_manuscript(manuscript)
    layout = layout or PrintLayout()
    layout.validate()
    page_size = (layout.width_in * inch, layout.height_in * inch)
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=page_size,
        rightMargin=max(layout.margin_in, layout.gutter_in) * inch,
        leftMargin=layout.margin_in * inch,
        topMargin=layout.margin_in * inch,
        bottomMargin=layout.margin_in * inch,
        title=report.title,
        author="PAPI KIDS PUBLISHING",
        subject=f"Épreuve intérieure — {report.age_range} ans",
    )
    base = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "BookTitle", parent=base["Title"], alignment=TA_CENTER,
        fontName="Helvetica-Bold", fontSize=24, leading=30, spaceAfter=24,
    )
    chapter_style = ParagraphStyle(
        "ChapterTitle", parent=base["Heading1"], alignment=TA_LEFT,
        fontName="Helvetica-Bold", fontSize=18, leading=22, spaceAfter=16,
    )
    body_style = ParagraphStyle(
        "BookBody", parent=base["BodyText"], fontName="Helvetica",
        fontSize=11, leading=16, spaceAfter=10,
    )
    synopsis_style = ParagraphStyle(
        "Synopsis", parent=body_style, fontName="Helvetica-Oblique",
        textColor=colors.HexColor("#444444"),
    )
    story = [
        Spacer(1, 1.5 * inch),
        Paragraph(_escape(report.title), title_style),
        Paragraph(f"Pour les enfants de {report.age_range} ans", body_style),
        PageBreak(),
        Paragraph("Synopsis", chapter_style),
        Paragraph(_escape(manuscript["synopsis"]), synopsis_style),
    ]
    for index, chapter in enumerate(manuscript["chapters"], 1):
        story.append(PageBreak())
        story.append(Paragraph(f"{index}. {_escape(chapter['title'])}", chapter_style))
        for paragraph in chapter["text"].split("\n\n"):
            if paragraph.strip():
                story.append(Paragraph(_escape(paragraph.strip()), body_style))
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(page_size[0] / 2, 0.25 * inch, str(doc.page))
        canvas.restoreState()
    try:
        document.build(story, onFirstPage=footer, onLaterPages=footer)
    except Exception as exc:
        raise PrintPdfError("Impossible de composer l'épreuve PDF.") from exc
    result = buffer.getvalue()
    if not result.startswith(b"%PDF-") or not result.rstrip().endswith(b"%%EOF"):
        raise PrintPdfError("Le fichier PDF généré est incomplet.")
    return result


def _escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
