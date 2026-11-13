"""Deterministic multi-page static site generation for PAPI WEB BUILDER.

Consumes the validated architecture contract; never executes user-supplied code.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

from papi_core.site_architecture import build_site_architecture
from papi_core.website_builder import CSS, WebsiteBuilderError, _text
from papi_core.website_sections import render_page_sections, WebsiteSectionError

MAX_PAGE_BYTES = 256_000

SECTOR_DESIGNS = {
    "corporate": {"label": "Entreprise", "primary": "#14283f", "accent": "#805b35", "surface": "#f3f6f8", "layout": "editorial"},
    "ecommerce": {"label": "Commerce", "primary": "#172d27", "accent": "#8a4f1d", "surface": "#f7f5f0", "layout": "commerce"},
    "hospitality": {"label": "Hôtellerie", "primary": "#26364a", "accent": "#79582f", "surface": "#f5f1eb", "layout": "hospitality"},
    "professional_services": {"label": "Services professionnels", "primary": "#202a46", "accent": "#53638b", "surface": "#f4f5fa", "layout": "editorial"},
    "education": {"label": "Éducation", "primary": "#183c46", "accent": "#80571b", "surface": "#f1f7f6", "layout": "learning"},
    "health": {"label": "Santé", "primary": "#17423d", "accent": "#28685f", "surface": "#f1f7f5", "layout": "care"},
}
SECTOR_COPY = {
    "corporate": ("Une vision claire. Des résultats durables.", "Découvrez notre approche et nos engagements."),
    "ecommerce": ("Vos essentiels, soigneusement sélectionnés.", "Explorez notre sélection et trouvez ce qu'il vous faut."),
    "hospitality": ("Un séjour pensé autour de vous.", "Découvrez nos espaces, nos expériences et nos attentions."),
    "professional_services": ("L'expertise au service de vos ambitions.", "Une équipe engagée à vos côtés, de la stratégie à l'action."),
    "education": ("Apprendre, progresser, réussir.", "Un environnement stimulant pour développer chaque potentiel."),
    "health": ("Votre santé mérite toute notre attention.", "Une prise en charge attentive, claire et centrée sur vous."),
}


def _relative_luminance(color: str) -> float:
    """Return WCAG relative luminance for a validated #RRGGBB color."""
    if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        raise MultiPageBuilderError("Couleur invalide pour le calcul de contraste.")
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    """Calculate WCAG contrast ratio between two opaque sRGB colors."""
    first, second = sorted((_relative_luminance(foreground), _relative_luminance(background)), reverse=True)
    return (first + 0.05) / (second + 0.05)


class MultiPageBuilderError(ValueError):
    """Invalid multi-page project or unsafe filesystem operation."""


def _safe_root(workspace: str | Path, slug: str) -> Path:
    try:
        from papi_core.website_builder import _project_dir
        return _project_dir(workspace, slug)
    except WebsiteBuilderError as exc:
        raise MultiPageBuilderError(str(exc)) from exc


def _render_page(project_name: str, page: dict[str, Any], pages: list[dict[str, Any]], industry: str, tagline: str, custom_sections: str) -> str:
    slug = page["slug"]
    prefix = "" if slug == "home" else "../"
    stylesheet = f"{prefix}styles.css"
    nav = []
    for item in pages:
        href = ("index.html" if item["slug"] == "home" else f"{item['slug']}/index.html") if slug == "home" else ("../index.html" if item["slug"] == "home" else f"../{item['slug']}/index.html")
        active = item["slug"] == slug
        nav.append(f'<a href="{html.escape(href, quote=True)}"' + (' aria-current="page"' if active else "") + f'>{html.escape(item["title"])}</a>')
    title = html.escape(page["title"])
    name = html.escape(project_name)
    purpose = html.escape(page["purpose"])
    design = SECTOR_DESIGNS[industry]
    hero_title, hero_copy = SECTOR_COPY[industry]
    is_home = slug == "home"
    contact = next((p for p in pages if p["slug"] == "contact"), None)
    contact_link = ("" if slug == "home" else "../") + ("contact/index.html" if contact else "index.html")
    hero = f'<section class="hero hero--{design["layout"]}" aria-labelledby="page-title"><div class="hero-copy"><p class="eyebrow">{html.escape(tagline or design["label"])}</p><h1 id="page-title">{title if not is_home else html.escape(hero_title)}</h1><p class="hero-description">{purpose if not is_home else html.escape(hero_copy)}</p><a class="primary-link" href="{contact_link}">Découvrir nos solutions <span aria-hidden="true">↗</span></a></div><div class="hero-visual" aria-hidden="true"><div class="visual-orbit"></div><div class="visual-core"></div><span class="visual-label">{html.escape(design["label"])}</span></div></section>'
    cards = [
        ("Une approche claire", "Des priorités définies et une expérience structurée."),
        ("Un service attentif", "Des réponses adaptées à vos besoins et à votre contexte."),
        ("Un engagement durable", "Des solutions conçues pour évoluer avec vous."),
    ]
    card_html = "".join(f'<article class="feature-card"><span class="feature-index">0{i}</span><h3>{html.escape(head)}</h3><p>{html.escape(body)}</p></article>' for i,(head,body) in enumerate(cards,1))
    feature_section = custom_sections or (f'<section class="features" aria-labelledby="features-title"><div class="section-heading"><p class="eyebrow">Notre différence</p><h2 id="features-title">Une expérience conçue avec intention.</h2></div><div class="feature-grid">{card_html}</div></section>' if is_home else f'<section class="content-panel"><p class="eyebrow">{html.escape(design["label"])}</p><h2>{title}</h2><p>{purpose}</p></section>')
    links = "\n      ".join(nav)
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


def generate_multi_page_project(
    workspace: str | Path, slug: str, spec: dict[str, Any], architecture_brief: dict[str, Any]
) -> dict[str, Any]:
    """Generate a safe multi-page static site with a sector-specific design system."""
    root = _safe_root(workspace, slug)
    if root.exists():
        raise MultiPageBuilderError("Le projet existe déjà.")
    if not isinstance(spec, dict) or set(spec) - {"name", "industry", "tagline", "sections"} or "name" not in spec:
        raise MultiPageBuilderError("Brief projet invalide : name, industry et tagline sont les seuls champs admis.")
    project_name = _text(spec["name"], "name", limit=100)
    industry = spec.get("industry", "corporate")
    if not isinstance(industry, str) or industry not in SECTOR_DESIGNS:
        raise MultiPageBuilderError("Secteur non pris en charge.")
    tagline = _text(spec.get("tagline", SECTOR_DESIGNS[industry]["label"]), "tagline", limit=100)
    architecture = build_site_architecture(architecture_brief)
    if architecture["project_name"] != project_name:
        raise MultiPageBuilderError("Le nom du projet doit correspondre au sitemap.")
    pages = architecture["pages"]
    page_slugs = {page["slug"] for page in pages}
    page_sections = spec.get("sections", {})
    if not isinstance(page_sections, dict) or set(page_sections) - page_slugs:
        raise MultiPageBuilderError("Les sections doivent être associées à des pages existantes.")
    root.mkdir(parents=True, exist_ok=False)
    generated: list[str] = []
    try:
        for page in pages:
            relative = Path(page["file"])
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                custom_sections = render_page_sections(page_sections.get(page["slug"], []), page["slug"], page_slugs)
            except WebsiteSectionError as exc:
                raise MultiPageBuilderError(str(exc)) from exc
            rendered = _render_page(project_name, page, pages, industry, tagline, custom_sections)
            if len(rendered.encode("utf-8")) > MAX_PAGE_BYTES:
                raise MultiPageBuilderError("Page trop volumineuse.")
            destination.write_text(rendered, encoding="utf-8")
            generated.append(relative.as_posix())
        design = SECTOR_DESIGNS[industry]
        sector_css = f"""
:root {{ --ink: {design['primary']}; --accent: {design['accent']}; --paper: {design['surface']}; }}
.hero-visual {{ min-height:330px; position:relative; display:grid; place-items:center; overflow:hidden; background:linear-gradient(145deg,#e8edf2,#f5e7d7); }}
.hero--commerce .hero-visual {{ border-radius:24px; background:linear-gradient(135deg,#e5eddf,#f8e5ce); }}
.hero--hospitality .hero-visual {{ border-radius:48% 48% 12px 12px; background:linear-gradient(145deg,#e8dfd1,#f6eee2); }}
.hero--learning .hero-visual {{ border-radius:28px 100px 28px 100px; background:linear-gradient(145deg,#d9e9e6,#f5e8d2); }}
.hero--care .hero-visual {{ border-radius:50%; background:radial-gradient(circle,#fff,#dceee8); }}
.visual-orbit {{ width:240px; height:240px; border:1px solid rgba(16,29,45,.2); border-radius:50%; position:absolute; }}
.visual-core {{ width:135px; height:135px; border-radius:38% 62% 50% 50%; background:linear-gradient(145deg,var(--ink),var(--accent)); box-shadow:0 25px 60px rgba(16,29,45,.15); }}
.visual-label {{ position:absolute; bottom:1.5rem; color:var(--muted); letter-spacing:.15em; text-transform:uppercase; font-size:.7rem; }}
.features {{ padding-block:4rem 6rem; }}
.section-heading {{ max-width:650px; margin-bottom:2rem; }}
.section-heading h2,.closing-cta h2 {{ font-size:clamp(2rem,4vw,3.4rem); margin:.5rem 0; }}
.feature-grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:1rem; }}
.feature-card,.content-panel {{ padding:2rem; border:1px solid var(--line); border-radius:12px; background:#fff; }}
.content-section {{ padding-block:3rem; }}
.content-intro {{ max-width:850px; }}
.content-section h2 {{ max-width:760px; }}
.stats-grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:1rem; }}
.stat-card {{ padding:1.5rem; border:1px solid var(--line); background:#fff; border-radius:12px; display:flex; flex-direction:column; gap:.5rem; }}
.stat-card strong {{ font:800 clamp(1.8rem,4vw,3rem) var(--font-display); color:var(--ink); }}
.stat-card span {{ color:var(--muted); }}
.faq-section details {{ padding:1rem 0; border-bottom:1px solid var(--line); }}
.faq-section summary {{ cursor:pointer; font-weight:700; }}
.faq-section details p {{ color:var(--muted); }}
.section-cta {{ padding:2rem; border:1px solid var(--line); border-radius:16px; background:var(--paper); }}
.feature-index {{ color:var(--accent); font-weight:800; letter-spacing:.12em; }}
.business-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,230px),1fr)); gap:1rem; }}
.product-card,.team-card,.testimonial-card,.service-card {{ min-width:0; padding:1.5rem; border:1px solid var(--line); border-radius:14px; background:#fff; }}
.product-card h3,.team-card h3,.service-card h3 {{ margin-top:0; font-family:var(--font-display); }}
.product-price,.team-role {{ color:var(--ink); font-weight:750; }}
.testimonial-card {{ margin:0; }}
.testimonial-card blockquote {{ margin:0 0 1.25rem; line-height:1.65; }}
.testimonial-card figcaption {{ display:flex; flex-direction:column; gap:.2rem; }}
.testimonial-card figcaption span,.content-disclaimer {{ color:var(--muted); font-size:.85rem; }}
.content-disclaimer {{ padding:.7rem 1rem; border-left:3px solid var(--accent); background:var(--paper); }}

.feature-card h3 {{ font-family:var(--font-display); font-size:1.2rem; }}
.feature-card p,.content-panel p {{ color:var(--muted); }}
.content-panel {{ max-width:850px; margin-block:2rem 5rem; }}
.closing-cta {{ display:flex; justify-content:space-between; align-items:center; gap:2rem; padding:3rem; margin-block:2rem 5rem; border-radius:16px; background:var(--white); border:1px solid var(--line); }}
@media(max-width:800px) {{ .feature-grid,.stats-grid {{ grid-template-columns:1fr; }} .closing-cta {{ align-items:flex-start; flex-direction:column; padding:2rem; }} .hero-visual {{ min-height:260px; }} }}
"""
        (root / "styles.css").write_text(CSS + sector_css + """
.site-header nav { display:flex; flex-wrap:wrap; gap:1.1rem; align-items:center; }
.site-header nav a { color:var(--muted); text-decoration:none; font-size:.9rem; font-weight:600; }
.site-header nav a[aria-current="page"] { color:var(--ink); text-decoration:underline; text-decoration-color:var(--accent); text-underline-offset:.35rem; }
.breadcrumbs { padding-top:2rem; color:var(--muted); font-size:.85rem; }
.breadcrumbs a { color:inherit; }
.hero { padding-block:4rem; }
/* Prevent intrinsic grid sizing and long copy from widening narrow viewports. */
.hero > *, .hero-copy, .hero-visual, .content-section, .feature-card { min-width:0; max-width:100%; }
.hero h1, .hero p, .content-section h2, .content-section p, .feature-card h3, .feature-card p { overflow-wrap:anywhere; }
@media(max-width:800px) { .header-inner { align-items:flex-start; flex-direction:column; gap:.8rem; padding-block:1rem; } .hero { grid-template-columns:minmax(0,1fr); } }
""", encoding="utf-8")
        sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        for page in pages:
            loc = "/" if page["slug"] == "home" else f"/{page['slug']}/"
            sitemap += f"  <url><loc>{xml_escape(loc)}</loc></url>\n"
        sitemap += "</urlset>\n"
        (root / "sitemap.xml").write_text(sitemap, encoding="utf-8")
        manifest = {
            "slug": slug, "project_name": project_name, "industry": industry, "tagline": tagline,
            "engine": "deterministic-multi-page-static", "design_system": design,
            "architecture": architecture,
            "generated_files": sorted(generated + ["styles.css", "sitemap.xml"]),
            "published": False,
        }
        (root / "project.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception:
        import shutil
        shutil.rmtree(root, ignore_errors=True)
        raise
    return {"slug": slug, "files": sorted(generated + ["styles.css", "sitemap.xml", "project.json"]), "page_count": len(pages), "industry": industry, "published": False, "preview": "static_file_only"}


def multi_page_quality_report(workspace: str | Path, slug: str) -> dict[str, Any]:
    root = _safe_root(workspace, slug)
    manifest_path = root / "project.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise MultiPageBuilderError("Manifest multi-pages absent ou non sûr.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("generated_files")
    if not isinstance(files, list) or len(files) != len(set(files)):
        raise MultiPageBuilderError("Manifeste de fichiers invalide.")
    expected_pages = [page["file"] for page in manifest["architecture"]["pages"]]
    expected_files = sorted(expected_pages + ["styles.css", "sitemap.xml"])
    if sorted(files) != expected_files:
        raise MultiPageBuilderError("Le manifeste ne correspond pas aux fichiers attendus.")
    checks = {
        "page_count_matches_architecture": len(expected_pages) == len(manifest["architecture"]["pages"]),
        "shared_stylesheet": (root / "styles.css").is_file(),
        "sitemap_present": (root / "sitemap.xml").is_file(),
        "sector_design_tokens": manifest.get("industry") in SECTOR_DESIGNS,
        "sector_accent_wcag_aa": False,
        "all_pages_exist": True, "all_internal_navigation_resolves": True,
        "no_script_execution": True, "semantic_headings": True,
    }
    stylesheet = (root / "styles.css").read_text(encoding="utf-8")
    accent_values = re.findall(r"--accent:\s*(#[0-9a-fA-F]{6})", stylesheet)
    paper_values = re.findall(r"--paper:\s*(#[0-9a-fA-F]{6})", stylesheet)
    if accent_values and paper_values:
        checks["sector_accent_wcag_aa"] = (
            contrast_ratio(accent_values[-1], "#ffffff") >= 4.5
            and contrast_ratio(accent_values[-1], paper_values[-1]) >= 4.5
        )
    for name in files:
        path = root / name
        resolved = path.resolve()
        if path.is_symlink() or not path.is_file() or Path(name).is_absolute() or ".." in Path(name).parts or root.resolve() not in resolved.parents:
            raise MultiPageBuilderError("Chemin de fichier du manifeste non sûr.")
    for name in expected_pages:
        document = (root / name).read_text(encoding="utf-8")
        checks["all_pages_exist"] &= "<!doctype html>" in document and 'name="viewport"' in document
        checks["no_script_execution"] &= "<script" not in document.lower()
        checks["semantic_headings"] &= "<h1 " in document and "<main " in document
        for href in re.findall(r'<a\s+href="([^"]+)"', document):
            if href.startswith(("#", "https://", "mailto:")):
                continue
            resolved = (root / Path(name).parent / href).resolve()
            if root.resolve() not in resolved.parents and resolved != root.resolve():
                checks["all_internal_navigation_resolves"] = False
            elif not resolved.is_file():
                checks["all_internal_navigation_resolves"] = False
    return {"slug": slug, "checks": checks, "passed": all(checks.values()), "preview": "static_file_only"}
