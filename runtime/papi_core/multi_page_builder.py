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


class MultiPageBuilderError(ValueError):
    """Invalid multi-page project or unsafe filesystem operation."""


def _safe_root(workspace: str | Path, slug: str) -> Path:
    try:
        from papi_core.website_builder import _project_dir
        return _project_dir(workspace, slug)
    except WebsiteBuilderError as exc:
        raise MultiPageBuilderError(str(exc)) from exc


def _render_page(project_name: str, page: dict[str, Any], pages: list[dict[str, Any]]) -> str:
    slug = page["slug"]
    prefix = "" if slug == "home" else "../"
    stylesheet = f"{prefix}styles.css"
    nav = []
    for item in pages:
        if slug == "home":
            href = "index.html" if item["slug"] == "home" else f"{item['slug']}/index.html"
        else:
            href = "../index.html" if item["slug"] == "home" else f"../{item['slug']}/index.html"
        active = item["slug"] == slug
        nav.append(
            f'<a href="{html.escape(href, quote=True)}"'
            + (' aria-current="page"' if active else "")
            + f'>{html.escape(item["title"])}</a>'
        )
    title = html.escape(page["title"])
    name = html.escape(project_name)
    purpose = html.escape(page["purpose"])
    links = "\n      ".join(nav)
    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} | {name}</title>
  <meta name="description" content="{html.escape(page['purpose'][:155], quote=True)}">
  <meta name="theme-color" content="#101d2d">
  <link rel="stylesheet" href="{stylesheet}">
</head>
<body>
  <a class="skip-link" href="#main-content">Aller au contenu</a>
  <header class="site-header"><div class="shell header-inner">
    <a class="brand" href="{prefix}" aria-label="Accueil — {name}"><span class="brand-mark" aria-hidden="true">P</span><span>{name}</span></a>
    <nav aria-label="Navigation principale">{links}</nav>
  </div></header>
  <main id="main-content" class="shell">
    <nav class="breadcrumbs" aria-label="Fil d’Ariane"><a href="{prefix}index.html">Accueil</a><span aria-hidden="true"> / </span><span aria-current="page">{title}</span></nav>
    <section class="hero-page" aria-labelledby="page-title">
      <p class="eyebrow"> {name} </p>
      <h1 id="page-title">{title}</h1>
      <p class="hero-description">{purpose}</p>
    </section>
    <section class="requirement-panel" aria-labelledby="scope-title">
      <h2 id="scope-title">Ce que vous trouverez ici</h2>
      <p>{purpose}</p>
    </section>
  </main>
  <footer class="site-footer"><div class="shell footer-inner"><span>© {name}</span><span>Conçu avec exigence.</span></div></footer>
</body>
</html>
"""


def generate_multi_page_project(
    workspace: str | Path, slug: str, spec: dict[str, Any], architecture_brief: dict[str, Any]
) -> dict[str, Any]:
    """Generate a complete, linked static page tree from a validated sitemap."""
    root = _safe_root(workspace, slug)
    if root.exists():
        raise MultiPageBuilderError("Le projet existe déjà.")
    if not isinstance(spec, dict) or set(spec) != {"name"}:
        raise MultiPageBuilderError("Le brief projet doit contenir uniquement name.")
    project_name = _text(spec["name"], "name", limit=100)
    architecture = build_site_architecture(architecture_brief)
    if architecture["project_name"] != project_name:
        raise MultiPageBuilderError("Le nom du projet doit correspondre au sitemap.")
    pages = architecture["pages"]
    root.mkdir(parents=True, exist_ok=False)
    generated: list[str] = []
    try:
        for page in pages:
            relative = Path(page["file"])
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            rendered = _render_page(project_name, page, pages)
            if len(rendered.encode("utf-8")) > MAX_PAGE_BYTES:
                raise MultiPageBuilderError("Page trop volumineuse.")
            destination.write_text(rendered, encoding="utf-8")
            generated.append(relative.as_posix())
        (root / "styles.css").write_text(
            CSS + """
.site-header nav { display:flex; flex-wrap:wrap; gap:1.1rem; align-items:center; }
.site-header nav a { color:var(--muted); text-decoration:none; font-size:.9rem; font-weight:600; }
.site-header nav a[aria-current="page"] { color:var(--ink); text-decoration:underline; text-decoration-color:var(--accent); text-underline-offset:.35rem; }
.breadcrumbs { padding-top:2rem; color:var(--muted); font-size:.85rem; }
.breadcrumbs a { color:inherit; }
.hero-page { padding-block:5rem 3rem; max-width:850px; }
.hero-page h1 { margin-block:1rem; }
.requirement-panel { max-width:850px; margin-bottom:6rem; padding:2rem; background:#fff; border:1px solid var(--line); border-radius:12px; }
.requirement-panel h2 { font-size:clamp(1.6rem,3vw,2.4rem); }
@media(max-width:800px) { .header-inner { align-items:flex-start; flex-direction:column; gap:.8rem; padding-block:1rem; } .hero-page { padding-block:3rem 2rem; } }
""" ,
            encoding="utf-8",
        )
        sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        for page in pages:
            loc = "/" if page["slug"] == "home" else f"/{page['slug']}/"
            sitemap += f"  <url><loc>{xml_escape(loc)}</loc></url>\n"
        sitemap += "</urlset>\n"
        (root / "sitemap.xml").write_text(sitemap, encoding="utf-8")
        manifest = {
            "slug": slug, "project_name": project_name,
            "engine": "deterministic-multi-page-static",
            "architecture": architecture, "generated_files": sorted(generated + ["styles.css", "sitemap.xml"]),
            "published": False,
        }
        (root / "project.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception:
        import shutil
        shutil.rmtree(root, ignore_errors=True)
        raise
    return {"slug": slug, "files": sorted(generated + ["styles.css", "sitemap.xml", "project.json"]), "page_count": len(pages), "published": False, "preview": "static_file_only"}


def multi_page_quality_report(workspace: str | Path, slug: str) -> dict[str, Any]:
    root = _safe_root(workspace, slug)
    manifest_path = root / "project.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise MultiPageBuilderError("Manifest multi-pages absent ou non sûr.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("generated_files")
    if not isinstance(files, list) or len(files) != len(set(files)):
        raise MultiPageBuilderError("Manifeste de fichiers invalide.")
    page_files = [name for name in files if name.endswith("/index.html") or name == "index.html"]
    checks = {"page_count_matches_architecture": len(page_files) == len(manifest["architecture"]["pages"]), "shared_stylesheet": (root / "styles.css").is_file(), "sitemap_present": (root / "sitemap.xml").is_file(), "all_pages_exist": True, "all_internal_navigation_resolves": True, "no_script_execution": True}
    for name in files:
        path = root / name
        if path.is_symlink() or not path.is_file() or Path(name).is_absolute() or ".." in Path(name).parts:
            raise MultiPageBuilderError("Chemin de fichier du manifeste non sûr.")
    for name in page_files:
        document = (root / name).read_text(encoding="utf-8")
        checks["all_pages_exist"] &= "<!doctype html>" in document and 'name="viewport"' in document
        checks["no_script_execution"] &= "<script" not in document.lower()
        import re
        for href in re.findall(r'<a\s+href="([^"]+)"', document):
            if href.startswith(("#", "https://", "mailto:")):
                continue
            resolved = (root / Path(name).parent / href).resolve()
            if root.resolve() not in resolved.parents and resolved != root.resolve():
                checks["all_internal_navigation_resolves"] = False
            elif not resolved.is_file():
                checks["all_internal_navigation_resolves"] = False
    return {"slug": slug, "checks": checks, "passed": all(checks.values()), "preview": "static_file_only"}
