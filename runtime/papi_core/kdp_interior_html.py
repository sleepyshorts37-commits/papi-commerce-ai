"""Generate print-sized HTML interior pages from approved source text and image assets.

The HTML is a layout artifact, not a KDP-ready PDF. Dimensions must come from the
current official KDP template; no trim, bleed, gutter or font metrics are guessed.
"""
from __future__ import annotations

import base64
from html import escape
import re
from typing import Any


class KDPInteriorRenderError(ValueError):
    """Missing source content, image asset or explicit print/layout dimensions."""


_PAGE = re.compile(r"^### Page (\d+)\s+[—-]\s+(.+?)\s*$", re.MULTILINE)
_ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}
_ALLOWED_ALIGN = {"left", "center", "right"}


def _number(value: Any, field: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        raise KDPInteriorRenderError(f"Valeur de mise en page invalide : {field}.")
    return float(value)


def parse_manuscript_pages(markdown: str) -> list[dict[str, Any]]:
    if not isinstance(markdown, str):
        raise KDPInteriorRenderError("Manuscrit absent.")
    matches = list(_PAGE.finditer(markdown))
    if len(matches) != 24:
        raise KDPInteriorRenderError(f"24 pages narratives attendues, {len(matches)} trouvées.")
    pages = []
    for index, match in enumerate(matches):
        number = int(match.group(1))
        if number != index + 1:
            raise KDPInteriorRenderError("Pagination du manuscrit non séquentielle.")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        body = markdown[match.end():end].strip()
        if not body:
            raise KDPInteriorRenderError(f"Texte vide page {number}.")
        pages.append({"page_id": f"page-{number:02d}", "page_number": number,
                      "heading": match.group(2).strip(), "body": body})
    return pages


def render_pkp0001_interior_html(
    *,
    manuscript_markdown: str,
    images_by_page: dict[str, dict[str, Any]],
    page_width_in: float,
    page_height_in: float,
    layout_by_page: dict[str, dict[str, Any]],
    font_family: str = "Noto Sans",
) -> str:
    """Render 24 full-bleed image pages with editable text overlays as HTML."""
    width = _number(page_width_in, "page_width_in", 1, 20)
    height = _number(page_height_in, "page_height_in", 1, 20)
    if font_family not in {"Noto Sans", "Arial", "DejaVu Sans", "Liberation Sans"}:
        raise KDPInteriorRenderError("Police non autorisée dans le gabarit.")
    pages = parse_manuscript_pages(manuscript_markdown)
    if not isinstance(images_by_page, dict) or set(images_by_page) != {p["page_id"] for p in pages}:
        raise KDPInteriorRenderError("Il faut exactement une image finale par page, sans doublon.")
    if not isinstance(layout_by_page, dict) or set(layout_by_page) != {p["page_id"] for p in pages}:
        raise KDPInteriorRenderError("Il faut une fiche de placement de texte pour chacune des 24 pages.")

    rendered = []
    for page in pages:
        page_id = page["page_id"]
        asset = images_by_page[page_id]
        layout = layout_by_page[page_id]
        image_bytes = asset.get("image_bytes") if isinstance(asset, dict) else None
        mime = asset.get("mime_type") if isinstance(asset, dict) else None
        if not isinstance(image_bytes, bytes) or not image_bytes or mime not in _ALLOWED_MIME:
            raise KDPInteriorRenderError(f"Image finale ou MIME invalide pour {page_id}.")
        x = _number(layout.get("x"), f"{page_id}.x", 0, 0.95)
        y = _number(layout.get("y"), f"{page_id}.y", 0, 0.95)
        w = _number(layout.get("width"), f"{page_id}.width", 0.05, 1)
        h = _number(layout.get("height"), f"{page_id}.height", 0.05, 1)
        if x + w > 1 or y + h > 1:
            raise KDPInteriorRenderError(f"Zone de texte hors page pour {page_id}.")
        font_size = _number(layout.get("font_size_pt"), f"{page_id}.font_size_pt", 10, 48)
        align = layout.get("align", "left")
        if align not in _ALLOWED_ALIGN:
            raise KDPInteriorRenderError(f"Alignement invalide pour {page_id}.")
        opacity = _number(layout.get("panel_opacity", 0.82), f"{page_id}.panel_opacity", 0, 1)
        text_color = layout.get("text_color", "#17212b")
        if not isinstance(text_color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", text_color):
            raise KDPInteriorRenderError(f"Couleur texte invalide pour {page_id}.")
        data_uri = "data:" + mime + ";base64," + base64.b64encode(image_bytes).decode("ascii")
        paragraphs = []
        for block in re.split(r"\n\s*\n", page["body"]):
            clean = block.strip()
            if clean:
                paragraphs.append("<p>" + escape(clean).replace("\n", "<br>") + "</p>")
        text_html = "\n".join(paragraphs)
        rendered.append(
            f'<section class="page" data-page="{page["page_number"]}">'
            f'<img class="art" src="{data_uri}" alt="Illustration page {page["page_number"]}">'
            f'<div class="copy" style="left:{x*100:.3f}%;top:{y*100:.3f}%;'
            f'width:{w*100:.3f}%;height:{h*100:.3f}%;font-size:{font_size:.2f}pt;'
            f'text-align:{align};color:{text_color};background:rgba(255,255,255,{opacity:.3f})">'
            f'<h2>{escape(page["heading"])}</h2>{text_html}</div></section>'
        )
    return (
        "<!doctype html><html lang=\"fr\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>PKP-0001 — Intérieur de production</title><style>"
        f"@page{{size:{width:.4f}in {height:.4f}in;margin:0}}"
        "*{box-sizing:border-box}html,body{margin:0;padding:0}"
        f"body{{font-family:'{font_family}',sans-serif}}"
        f".page{{position:relative;width:{width:.4f}in;height:{height:.4f}in;"
        "overflow:hidden;page-break-after:always;break-after:page;background:#fff}}"
        ".page:last-child{page-break-after:auto;break-after:auto}"
        ".art{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}"
        ".copy{position:absolute;overflow:hidden;padding:0.16in 0.18in;line-height:1.28;"
        "border-radius:0.04in}.copy h2{font-size:1.12em;margin:0 0 0.08in;font-weight:700}"
        ".copy p{margin:0 0 0.07in;orphans:2;widows:2}"
        "@media screen{body{background:#555}.page{margin:16px auto;box-shadow:0 2px 12px #222}}"
        "</style></head><body>" + "\n".join(rendered) + "</body></html>"
    )
