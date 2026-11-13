"""Deterministic multi-page static site generation for PAPI WEB BUILDER.

Consumes the validated architecture contract; never executes user-supplied code.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

from papi_core.site_architecture import build_site_architecture
from papi_core.website_builder import CSS, WebsiteBuilderError, _text

MAX_PAGE_BYTES = 256_000

SECTOR_DESIGNS = {
    "corporate": {"label": "Entreprise", "primary": "#14283f", "accent": "#bd925d", "surface": "#f3f6f8", "layout": "editorial"},
    "ecommerce": {"label": "Commerce", "primary": "#172d27", "accent": "#d58a45", "surface": "#f7f5f0", "layout": "commerce"},
    "hospitality": {"label": "Hôtellerie", "primary": "#26364a", "accent": "#c49b69", "surface": "#f5f1eb", "layout": "hospitality"},
    "professional_services": {"label": "Services professionnels", "primary": "#202a46", "accent": "#8b9bc8", "surface": "#f4f5fa", "layout": "editorial"},
    "education": {"label": "Éducation", "primary": "#183c46", "accent": "#d49a48", "surface": "#f1f7f6", "layout": "learning"},
    "health": {"label": "Santé", "primary": "#17423d", "accent": "#63a99a", "surface": "#f1f7f5", "layout": "care"},
}
SECTOR_COPY = {
    "corporate": ("Une vision claire. Des résultats durables.", "Découvrez notre approche et nos engagements."),
    "ecommerce": ("Vos essentiels, soigneusement sélectionnés.", "Explorez notre sélection et trouvez ce qu'il vous faut."),
    "hospitality": ("Un séjour pensé autour de vous.", "Découvrez nos espaces, nos expériences et nos attentions."),
    "professional_services": ("L'expertise au service de vos ambitions.", "Une équipe engagée à vos côtés, de la stratégie à l'action."),
    "education": ("Apprendre, progresser, réussir.", "Un environnement stimulant pour développer chaque potentiel."),
    "health": ("Votre santé mérite toute notre attention.", "Une prise en charge attentive, claire et centrée sur vous."),
}


class MultiPageBuilderError(ValueError):
    """Invalid multi-page project or unsafe filesystem operation."""


def _safe_root(workspace: str | Path, slug: str) -> Path:
    try:
        from papi_core.website_builder import _project_dir
        return _project_dir(workspace, slug)
    except WebsiteBuilderError as exc:
        raise MultiPageBuilderError(str(exc)) from exc


def _render_page(project_name: str, page: dict[str, Any], pages: list[dict[str, Any]], industry: str, tagline: str) -> str:
    slug = page["slug"]
    prefix = "" if slug == "home" else "../"
    stylesheet = f"{prefix}styles.css"
    nav = []
    for item in pages:
        href = ("index.html" if item["slug"] == "home" else f"{item['slug']}/index.html") if slug == "home" else ("../index.html" if item["slug"] == "home" else f"../{item['slug']}/index.html")
        active = item["slug"] == slug
        nav.append(f'<a href="{html.escape(href, quote=True)}"' + (' aria-current="page"' if active else "") + f'>{html.escape(item["title"])}</a>')
    title, name, purpose = (html.escape(page[key]) for key in ("title",))
    name = html.escape(project_name)
    purpose = html.escape(page["purpose"])
    design = SECTOR_DESIGNS[industry]
    hero_title, hero_copy = SECTOR_COPY[industry]
    is_home = slug == "home"
    hero = f'<section class="hero hero--{design["layout"]}" aria-labelledby="page-title"><div class="hero-copy"><p class="eyebrow">{html.escape(tagline or design["label"])}</p><h1 id="page-title">{title if not is_home else html.escape(hero_title)}</h1><p class="hero-description">{purpose if not is_home else html.escape(hero_copy)}</p><a class="primary-link" href="{prefix}contact/index.html">Découvrir nos solutions <span aria-hidden="true">↗</span></a></div><div class="hero-visual" aria-hidden="true"><div class="visual-orbit"></div><div class="visual-core"></div><span class="visual-label">{html.escape(design["label"])}</span></div></section>'
    cards = [
        ("Une approche claire", "Des priorités définies et une expérience structurée."),
        ("Un service attentif", "Des réponses adaptées à vos besoins et à votre contexte."),
        ("Un engagement durable", "Des solutions conçues pour évoluer avec vous."),
    ]
    card_html = "".join(f'<article class="feature-card"><span class="feature-index">0{i}</span><h3>{html.escape(head)}</h3><p>{html.escape(body)}</p></article>' for i,(head,body) in enumerate(cards,1))
    feature_section = f'<section class="features" aria-labelledby="features-title"><div class="section-heading"><p class="eyebrow">Notre différence</p><h2 id="features-title">Une expérience conçue avec intention.</h2></div><div class="feature-grid">{card_html}</div></section>' if is_home else f'<section class="content-panel"><p class="eyebrow">{html.escape(design["label"])}</p><h2>{title}</h2><p>{purpose}</p></section>'
    links = "\\n      ".join(nav)
    contact = next((p for p in pages if p["slug"] == "contact"), None)
    contact_link = ("" if slug == "home" else "../") + ("contact/index.html" if contact else "index.html")
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | {name}</title><meta name="description" content="{html.escape(page['purpose'][:155], quote=True)}">
<meta name="theme-color" content="{design['primary']}"><link rel="stylesheet" href="{stylesheet}">
</head>
<body class="sector-{industry}">
<a class="skip-link" href="#main-content">Aller au contenu</a>
<header class="site-header"><div class="shell header-inner"><a class="brand" href="{prefix}index.html"><span class="brand-mark" aria-hidden="true">P</span><span>{name}</span></a><nav aria-label="Navigation principale">{links}</nav></div></header>
<main id="main-content" class="shell">
<nav class="breadcrumbs" aria-label="Fil d’Ariane"><a href="{prefix}index.html">Accueil</a><span aria-hidden="true"> / </span><span aria-current="page">{title}</span></nav>
{hero}
{feature_section}
<section class="closing-cta"><div><p class="eyebrow">Passons à l'étape suivante</p><h2>Parlons de votre projet.</h2></div><a class="primary-link" href="{contact_link}">Nous contacter <span aria-hidden="true">↗</span></a></section>
</main>
<footer class="site-footer"><div class="shell footer-inner"><span>© {name}</span><span>{html.escape(design["label"])} · Conçu avec exigence</span></div></footer>
</body></html>
"""
