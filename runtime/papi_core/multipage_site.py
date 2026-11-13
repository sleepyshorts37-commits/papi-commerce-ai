"""Deterministic, local-only multi-page static site generator for PAPI."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from papi_core.content_generation import generate_commercial_content

PAGE_SLUG = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,28}[a-z0-9])?$")
MAX_PAGES = 6
MAX_TOTAL_HTML = 1_000_000
CSS = """:root{font-family:system-ui,-apple-system,'Segoe UI',sans-serif;color:#142337;background:#f7f8fa}
*{box-sizing:border-box}body{margin:0;line-height:1.65}a:focus-visible{outline:3px solid #a87943;outline-offset:3px}
.shell{width:min(100% - 2rem,1100px);margin:auto}.skip{position:absolute;left:-9999px}.skip:focus{left:1rem;top:1rem;background:white;padding:.5rem}
header{background:white;border-bottom:1px solid #e3e7ec}.head{display:flex;justify-content:space-between;align-items:center;gap:1rem;padding:1rem 0}
.brand{font-weight:800;text-decoration:none}.nav{display:flex;flex-wrap:wrap;gap:.8rem}.nav a{color:#334b63;text-decoration:none;font-size:.92rem}
main{padding:clamp(3rem,8vw,7rem) 0;min-height:65vh}h1{font-size:clamp(2.2rem,6vw,4.6rem);line-height:1.1;letter-spacing:-.04em;max-width:850px}
.lead{font-size:1.2rem;color:#526276;max-width:760px}.facts{padding-left:1.3rem}.notice{margin-top:2rem;padding:1rem;border-left:3px solid #a87943;background:#fff}
footer{background:#142337;color:#edf1f5;padding:1.5rem 0;font-size:.9rem}
@media(max-width:640px){.head{align-items:flex-start;flex-direction:column}.nav{gap:.6rem}main{padding:3rem 0}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{transition:none!important;animation:none!important}}
"""

class MultiPageSiteError(ValueError):
    """Invalid brief or unsafe multi-page project operation."""


def _safe_slug(value: Any) -> str:
    if not isinstance(value, str) or not PAGE_SLUG.fullmatch(value):
        raise MultiPageSiteError("Identifiant de page invalide.")
    return value


def _page_html(brand: str, page: dict[str, Any], content: dict[str, str],
               links: list[tuple[str, str]], stylesheet: str) -> str:
    esc = lambda value: html.escape(str(value), quote=True)
    nav = " ".join(f'<a href="{esc(href)}">{esc(label)}</a>' for label, href in links)
    facts = "".join(f"<li>{esc(fact)}</li>" for fact in page["facts"])
    body = esc(content["body"]).replace("\n", "<br>\n")
    return (
        '<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>{esc(page["title"])} | {esc(brand)}</title>\n'
        f'<meta name="description" content="{esc(page["summary"][:155])}">\n'
        f'<link rel="stylesheet" href="{esc(stylesheet)}">\n</head>\n<body>\n'
        '<a class="skip" href="#main">Aller au contenu</a>\n'
        f'<header><div class="shell head"><a class="brand" href="{esc("index.html" if stylesheet == "styles.css" else "../index.html")}">{esc(brand)}</a>'
        f'<nav class="nav" aria-label="Navigation principale">{nav}</nav></div></header>\n'
        f'<main class="shell" id="main"><p class="eyebrow">{esc(page["title"])}</p>'
        f'<h1>{esc(page["title"])}</h1><p class="lead">{esc(page["summary"])}</p>'
        f'<section aria-label="Présentation"><p>{body}</p><ul class="facts">{facts}</ul>'
        f'<p class="notice">{esc(content["disclaimer"])}</p></section></main>\n'
        f'<footer><div class="shell">{esc(brand)} — Informations à confirmer auprès de l’établissement.</div></footer>\n'
        '</body>\n</html>\n'
    )


def generate_multipage_site(workspace: str | Path, slug: str,
                            brief: dict[str, Any]) -> dict[str, Any]:
    """Generate 1 home page plus 1–5 internal pages from fact-checked briefs.

    Each page has its own validated facts. No network, publishing, or overwrites.
    """
    project_slug = _safe_slug(slug)
    if not isinstance(brief, dict) or set(brief) - {"brand", "sector", "audience", "tone", "cta", "pages"}:
        raise MultiPageSiteError("Brief multi-pages invalide.")
    brand, sector, pages = brief.get("brand"), brief.get("sector"), brief.get("pages")
    if not isinstance(pages, list) or not 2 <= len(pages) <= MAX_PAGES:
        raise MultiPageSiteError(f"Le site doit contenir entre 2 et {MAX_PAGES} pages.")
    if not isinstance(brand, str) or not isinstance(sector, str):
        raise MultiPageSiteError("Marque et secteur obligatoires.")
    slugs: set[str] = set()
    prepared = []
    for item in pages:
        if not isinstance(item, dict) or set(item) - {"slug", "title", "summary", "facts"}:
            raise MultiPageSiteError("Structure de page invalide.")
        page_slug = _safe_slug(item.get("slug"))
        if page_slug == "index" or page_slug in slugs:
            raise MultiPageSiteError("Identifiant de page réservé ou dupliqué.")
        slugs.add(page_slug)
        title, summary, facts = item.get("title"), item.get("summary"), item.get("facts")
        if not isinstance(summary, str) or not summary.strip() or len(summary) > 180:
            raise MultiPageSiteError("Résumé de page invalide (1 à 180 caractères).")
        if not isinstance(facts, list) or len(facts) > 7:
            raise MultiPageSiteError("Chaque page accepte au maximum 7 faits, en plus du résumé.")
        content = generate_commercial_content({
            "content_type": "business_page", "sector": sector, "brand": brand,
            "offer": title, "audience": brief.get("audience", "notre clientèle"),
            "facts": [summary.strip(), *facts], "tone": brief.get("tone", "professional"),
            "cta": brief.get("cta", "Contactez-nous pour en savoir plus."),
        })
        prepared.append({"slug": page_slug, "title": title, "summary": summary.strip(),
                         "facts": facts, "content": content})

    root = Path(workspace).resolve()
    target = (root / project_slug).resolve()
    if target.parent != root or target.exists():
        raise MultiPageSiteError("Chemin projet interdit ou projet déjà existant.")
    target.mkdir(parents=True, exist_ok=False)
    (target / "pages").mkdir()
    links = [(page["title"], f"pages/{page['slug']}.html") for page in prepared]
    all_files = ["index.html", "styles.css", "project.json"]
    for i, page in enumerate(prepared):
        hrefs = [("Accueil", "../index.html")]
        hrefs.extend((other["title"], f"{other['slug']}.html")
                     for other in prepared if other["slug"] != page["slug"])
        doc = _page_html(brand, page, page["content"], hrefs, "../styles.css")
        (target / "pages" / f"{page['slug']}.html").write_text(doc, encoding="utf-8")
        all_files.append(f"pages/{page['slug']}.html")
    home = prepared[0]
    home_doc = _page_html(brand, home, home["content"], links, "styles.css")
    (target / "index.html").write_text(home_doc, encoding="utf-8")
    (target / "styles.css").write_text(CSS, encoding="utf-8")
    manifest = {
        "slug": project_slug, "brand": brand, "sector": sector,
        "pages": [{"slug": p["slug"], "title": p["title"]} for p in prepared],
        "engine": "deterministic-multipage-v1", "published": False,
        "review_required": True,
    }
    (target / "project.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    total = sum((target / name).stat().st_size for name in all_files)
    if total > MAX_TOTAL_HTML:
        raise MultiPageSiteError("Taille totale du site supérieure à la limite autorisée.")
    return {
        "slug": project_slug, "path": str(target), "files": all_files,
        "page_count": len(prepared), "total_bytes": total,
        "review_required": True, "published": False, "network_used": False,
    }
