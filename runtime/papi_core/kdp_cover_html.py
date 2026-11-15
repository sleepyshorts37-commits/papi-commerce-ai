"""Generate print-sized HTML wrap-cover layout from a supplied KDP template."""
from __future__ import annotations

import base64
from html import escape
import re
from typing import Any


class KDPCoverRenderError(ValueError):
    """Missing cover artwork, template geometry or validated text placement."""


def _fraction(value: Any, field: str, *, allow_zero: bool = True) -> float:
    low = 0 if allow_zero else 0.001
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= 1:
        raise KDPCoverRenderError(f"Coordonnée de couverture invalide : {field}.")
    return float(value)


def render_pkp0001_cover_html(
    *,
    full_wrap_image: bytes,
    image_mime_type: str,
    cover_width_in: float,
    cover_height_in: float,
    official_template_ref: str,
    front_panel: dict[str, Any],
    back_panel: dict[str, Any],
    title: str,
    subtitle: str,
    back_blurb: str,
    author: str = "",
    title_box: dict[str, Any],
    back_text_box: dict[str, Any],
    spine_box: dict[str, Any] | None = None,
) -> str:
    if not isinstance(full_wrap_image, bytes) or not full_wrap_image:
        raise KDPCoverRenderError("Illustration complète de couverture absente.")
    if image_mime_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise KDPCoverRenderError("Format d'image de couverture non pris en charge.")
    for value, field in ((cover_width_in, "cover_width_in"), (cover_height_in, "cover_height_in")):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 1 <= value <= 30:
            raise KDPCoverRenderError(f"Dimension {field} invalide.")
    if not isinstance(official_template_ref, str) or not official_template_ref.strip():
        raise KDPCoverRenderError("Référence du gabarit KDP obligatoire.")
    for value, field in ((title, "title"), (subtitle, "subtitle"), (back_blurb, "back_blurb")):
        if not isinstance(value, str) or not value.strip() or len(value) > 2_000:
            raise KDPCoverRenderError(f"Texte {field} absent ou trop long.")
    if not isinstance(author, str) or len(author) > 160:
        raise KDPCoverRenderError("Nom d'auteur invalide.")

    def box(spec: dict[str, Any], name: str) -> tuple[float, float, float, float]:
        if not isinstance(spec, dict):
            raise KDPCoverRenderError(f"Zone {name} absente.")
        x = _fraction(spec.get("x"), name + ".x")
        y = _fraction(spec.get("y"), name + ".y")
        w = _fraction(spec.get("width"), name + ".width", allow_zero=False)
        h = _fraction(spec.get("height"), name + ".height", allow_zero=False)
        if x + w > 1 or y + h > 1:
            raise KDPCoverRenderError(f"Zone {name} hors couverture.")
        return x, y, w, h

    fx, fy, fw, fh = box(front_panel, "front_panel")
    bx, by, bw, bh = box(back_panel, "back_panel")
    tx, ty, tw, th = box(title_box, "title_box")
    rx, ry, rw, rh = box(back_text_box, "back_text_box")
    if not (tx >= fx and ty >= fy and tx + tw <= fx + fw and ty + th <= fy + fh):
        raise KDPCoverRenderError("Le titre doit rester dans le panneau avant.")
    if not (rx >= bx and ry >= by and rx + rw <= bx + bw and ry + rh <= by + bh):
        raise KDPCoverRenderError("Le résumé doit rester dans le panneau arrière.")
    spine_html = ""
    if spine_box is not None:
        sx, sy, sw, sh = box(spine_box, "spine_box")
        spine_title = escape(title)
        spine_html = (
            f'<div class="spine" style="left:{sx*100:.3f}%;top:{sy*100:.3f}%;'
            f'width:{sw*100:.3f}%;height:{sh*100:.3f}%">{spine_title}</div>'
        )
    uri = "data:" + image_mime_type + ";base64," + base64.b64encode(full_wrap_image).decode("ascii")
    author_html = f"<p class='author'>{escape(author)}</p>" if author.strip() else ""
    return (
        "<!doctype html><html lang='fr'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>PKP-0001 — Couverture</title><style>"
        f"@page{{size:{float(cover_width_in):.4f}in {float(cover_height_in):.4f}in;margin:0}}"
        "*{box-sizing:border-box}html,body{margin:0;padding:0}"
        f".wrap{{position:relative;width:{float(cover_width_in):.4f}in;"
        f"height:{float(cover_height_in):.4f}in;overflow:hidden}}"
        ".art{position:absolute;inset:0;width:100%;height:100%;object-fit:fill}"
        ".panel{position:absolute;overflow:hidden;padding:2%;background:rgba(255,255,255,.78);"
        "border-radius:1.5%}.front{font-family:'Noto Sans',sans-serif;text-align:center}"
        ".front h1{font-size:2em;line-height:1.05;margin:0 0 .2em}"
        ".front p{font-size:1em;margin:.2em}.back{font-family:'Noto Sans',sans-serif;"
        "font-size:1em;line-height:1.35}.spine{position:absolute;display:flex;align-items:center;"
        "justify-content:center;writing-mode:vertical-rl;transform:rotate(180deg);"
        "font-family:'Noto Sans',sans-serif;font-weight:bold;overflow:hidden}"
        "@media screen{body{background:#555}.wrap{margin:16px auto;box-shadow:0 2px 12px #222}}"
        "</style></head><body><main class='wrap' data-template='"
        + escape(official_template_ref, quote=True)
        + "'><img class='art' src='" + uri + "' alt='Illustration complète de couverture'>"
        + f'<section class="panel front" style="left:{tx*100:.3f}%;top:{ty*100:.3f}%;'
        + f'width:{tw*100:.3f}%;height:{th*100:.3f}%"><h1>{escape(title)}</h1>'
        + f'<p>{escape(subtitle)}</p>{author_html}</section>'
        + f'<section class="panel back" style="left:{rx*100:.3f}%;top:{ry*100:.3f}%;'
        + f'width:{rw*100:.3f}%;height:{rh*100:.3f}%">{escape(back_blurb)}</section>'
        + spine_html + "</main></body></html>"
    )
