"""Safe deterministic MVP for static PAPI WEB BUILDER projects.

No LLM, shell, network, hosting, or preview server is invoked by this module.
"""
from __future__ import annotations

import html
import json
import re
import zipfile
from pathlib import Path
from typing import Any

SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?$")
ALLOWED_FILES = ("index.html", "styles.css", "project.json")
MAX_TEXT = 240
MAX_HTML = 256_000


class WebsiteBuilderError(ValueError):
    """Invalid input or unsafe project operation."""


def _text(value: Any, field: str, *, limit: int = MAX_TEXT) -> str:
    if not isinstance(value, str):
        raise WebsiteBuilderError(f"{field} doit être du texte.")
    value = value.strip()
    if not value or len(value) > limit:
        raise WebsiteBuilderError(f"{field} doit contenir entre 1 et {limit} caractères.")
    if any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise WebsiteBuilderError(f"{field} contient des caractères de contrôle.")
    return value


def normalize_spec(spec: dict[str, Any]) -> dict[str, str]:
    if not isinstance(spec, dict):
        raise WebsiteBuilderError("Le brief doit être un objet.")
    allowed = {"name", "tagline", "description", "contact"}
    if set(spec) - allowed:
        raise WebsiteBuilderError("Champ du brief non autorisé.")
    return {
        "name": _text(spec.get("name"), "name", limit=100),
        "tagline": _text(spec.get("tagline"), "tagline"),
        "description": _text(spec.get("description"), "description", limit=1000),
        "contact": _text(spec.get("contact", "Contact à confirmer"), "contact"),
    }


def _render_html(spec: dict[str, str]) -> str:
    esc = lambda value: html.escape(value, quote=True)
    return (
        "<!doctype html>\n<html lang=\"fr\">\n<head>\n"
        "  <meta charset=\"utf-8\">\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"  <title>{esc(spec['name'])}</title>\n"
        f"  <meta name=\"description\" content=\"{esc(spec['description'][:155])}\">\n"
        "  <meta name=\"theme-color\" content=\"#101d2d\">\n"
        "  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">\n"
        "  <link rel=\"stylesheet\" href=\"styles.css\">\n"
        "</head>\n<body>\n"
        "<a class=\"skip-link\" href=\"#main-content\">Aller au contenu</a>\n"
        "<header class=\"site-header\"><div class=\"shell header-inner\">"
        f"<a class=\"brand\" href=\"#top\" aria-label=\"Accueil — {esc(spec['name'])}\">"
        "<span class=\"brand-mark\" aria-hidden=\"true\">P</span>"
        f"<span>{esc(spec['name'])}</span></a>"
        "<span class=\"header-note\">Présentation officielle</span></div></header>\n"
        "<main id=\"main-content\">\n"
        "<section class=\"hero shell\" id=\"top\" aria-labelledby=\"hero-title\">"
        "<div class=\"hero-copy\">"
        f"<p class=\"eyebrow\"><span class=\"eyebrow-line\"></span>{esc(spec['tagline'])}</p>"
        f"<h1 id=\"hero-title\">{esc(spec['name'])}</h1>"
        f"<p class=\"hero-description\">{esc(spec['description'])}</p>"
        "<a class=\"primary-link\" href=\"#contact\">Parlons de votre projet <span aria-hidden=\"true\">↗</span></a>"
        "</div><div class=\"hero-art\" aria-hidden=\"true\"><div class=\"art-orbit orbit-one\"></div>"
        "<div class=\"art-orbit orbit-two\"></div><div class=\"art-core\"><span></span></div>"
        "<div class=\"art-caption\">Excellence · Confiance · Impact</div></div></section>\n"
        "<section class=\"trust-band\" aria-label=\"Engagement\"><div class=\"shell trust-inner\">"
        "<span>Une approche exigeante</span><span>Un accompagnement humain</span>"
        "<span>Des solutions pensées pour durer</span></div></section>\n"
        "<section class=\"contact-section shell\" id=\"contact\" aria-labelledby=\"contact-title\">"
        "<div><p class=\"section-kicker\">Échangeons</p>"
        "<h2 id=\"contact-title\">Construisons la suite ensemble.</h2>"
        "<p class=\"contact-copy\">Notre équipe est à votre écoute pour répondre à vos questions.</p></div>"
        f"<div class=\"contact-card\"><span class=\"contact-label\">Nous contacter</span>"
        f"<p>{esc(spec['contact'])}</p></div></section>\n"
        "</main>\n<footer class=\"site-footer\"><div class=\"shell footer-inner\">"
        f"<span>© {esc(spec['name'])}</span><span>Conçu avec exigence.</span>"
        "</div></footer>\n</body>\n</html>\n"
    )


CSS = """@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root {
  color-scheme: light;
  --ink: #101d2d; --muted: #627184; --paper: #f7f8fa; --white: #fff;
  --accent: #b58a55; --accent-soft: #f0e7dc; --line: #e5e9ef;
  --font-body: 'DM Sans', system-ui, sans-serif;
  --font-display: 'Manrope', 'DM Sans', system-ui, sans-serif;
  font-family: var(--font-body); color: var(--ink); background: var(--paper);
  font-synthesis: none; text-rendering: optimizeLegibility;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; min-width: 320px; line-height: 1.65; }
a { color: inherit; }
a:focus-visible { outline: 3px solid var(--accent); outline-offset: 4px; }
.shell { width: min(100% - 3rem, 1180px); margin-inline: auto; }
.skip-link { position: absolute; left: 1rem; top: -5rem; z-index: 10; padding: .8rem 1rem; background: var(--white); }
.skip-link:focus { top: 1rem; }
.site-header { background: rgba(255,255,255,.92); border-bottom: 1px solid var(--line); }
.header-inner, .brand, .footer-inner { display: flex; align-items: center; justify-content: space-between; }
.header-inner { min-height: 82px; }
.brand { gap: .8rem; text-decoration: none; font-family: var(--font-display); font-weight: 800; letter-spacing: -.03em; }
.brand-mark { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 12px; color: white; background: var(--ink); }
.header-note, .trust-band { color: var(--muted); font-size: .82rem; }
.hero { min-height: 590px; display: grid; grid-template-columns: 1.1fr .9fr; align-items: center; gap: 4rem; padding-block: 6rem; }
.hero-copy { max-width: 660px; }
.eyebrow, .section-kicker { color: #8c673e; text-transform: uppercase; letter-spacing: .16em; font-size: .76rem; font-weight: 700; }
.eyebrow { display: flex; align-items: center; gap: .8rem; }
.eyebrow-line { width: 32px; height: 1px; background: var(--accent); }
h1, h2 { font-family: var(--font-display); letter-spacing: -.055em; line-height: 1.08; }
h1 { max-width: 720px; margin: 1.2rem 0; font-size: clamp(3rem, 6vw, 5.8rem); font-weight: 800; }
.hero-description { max-width: 590px; color: var(--muted); font-size: clamp(1.05rem, 1.5vw, 1.2rem); }
.primary-link { display: inline-flex; gap: 1.5rem; align-items: center; margin-top: 1.8rem; padding: .95rem 1.25rem; border-radius: 5px; background: var(--ink); color: white; text-decoration: none; font-weight: 700; transition: transform .2s ease, background .2s ease; }
.primary-link:hover { transform: translateY(-2px); background: #233b56; }
.hero-art { min-height: 350px; position: relative; display: grid; place-items: center; overflow: hidden; border-radius: 48% 48% 12px 12px; background: radial-gradient(circle at 50% 42%, #fff 0, #f0e7dc 42%, #e7edf2 100%); }
.art-orbit { position: absolute; width: 270px; height: 270px; border: 1px solid rgba(16,29,45,.17); border-radius: 50%; }
.orbit-two { width: 370px; height: 370px; border-style: dashed; }
.art-core { width: 150px; height: 150px; display: grid; place-items: center; border-radius: 42% 58% 55% 45%; background: linear-gradient(145deg, #142a40, #45617a); box-shadow: 0 25px 60px rgba(16,29,45,.22); transform: rotate(-12deg); }
.art-core span { width: 48px; height: 48px; border: 2px solid #e8cda8; border-radius: 50%; }
.art-caption { position: absolute; bottom: 2rem; color: #596779; font-size: .7rem; letter-spacing: .16em; text-transform: uppercase; }
.trust-band { border-block: 1px solid var(--line); background: #fff; }
.trust-inner { min-height: 84px; display: flex; justify-content: space-between; align-items: center; gap: 1.5rem; }
.contact-section { display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 3rem; padding-block: 7rem; }
h2 { max-width: 600px; margin: .6rem 0 1rem; font-size: clamp(2rem, 4vw, 3.5rem); }
.contact-copy { color: var(--muted); }
.contact-card { min-width: 260px; padding: 1.5rem; border: 1px solid var(--line); border-radius: 10px; background: white; box-shadow: 0 18px 50px rgba(16,29,45,.06); }
.contact-label { color: var(--muted); font-size: .76rem; text-transform: uppercase; letter-spacing: .12em; }
.contact-card p { margin-bottom: 0; font-weight: 700; overflow-wrap: anywhere; }
.site-footer { background: var(--ink); color: #dce3ea; font-size: .82rem; }
.footer-inner { min-height: 76px; gap: 1rem; }
@media (max-width: 800px) {
  .hero { grid-template-columns: 1fr; gap: 2.5rem; padding-block: 4rem; }
  .hero-art { min-height: 290px; }
  .contact-section { grid-template-columns: 1fr; gap: 1.5rem; padding-block: 4.5rem; }
  .trust-inner { flex-wrap: wrap; justify-content: flex-start; padding-block: 1.2rem; }
}
@media (max-width: 520px) {
  .shell { width: min(100% - 2rem, 1180px); }
  .header-inner { min-height: 68px; }
  .header-note { display: none; }
  .hero { padding-block: 3rem; }
  h1 { font-size: clamp(2.7rem, 13vw, 4rem); }
  .hero-art { min-height: 240px; }
  .art-orbit { width: 190px; height: 190px; }
  .orbit-two { width: 270px; height: 270px; }
  .art-core { width: 112px; height: 112px; }
  .trust-inner { display: grid; gap: .5rem; }
  .footer-inner { align-items: flex-start; flex-direction: column; justify-content: center; padding-block: 1rem; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *, *::before, *::after { transition-duration: .01ms !important; animation-duration: .01ms !important; }
}
"""


def _project_dir(workspace: str | Path, slug: str) -> Path:
    if not isinstance(slug, str) or not SLUG_RE.fullmatch(slug):
        raise WebsiteBuilderError("Identifiant projet invalide.")
    root = Path(workspace).resolve()
    target = (root / slug).resolve()
    if target.parent != root:
        raise WebsiteBuilderError("Chemin projet interdit.")
    return target


def generate_project(workspace: str | Path, slug: str, spec: dict[str, Any]) -> dict[str, Any]:
    """Generate a local static site; refuses to overwrite an existing project."""
    target = _project_dir(workspace, slug)
    normalized = normalize_spec(spec)
    if target.exists():
        raise WebsiteBuilderError("Le projet existe déjà ; utiliser update_project.")
    target.mkdir(parents=True, exist_ok=False)
    files = {
        "index.html": _render_html(normalized),
        "styles.css": CSS,
        "project.json": json.dumps({"slug": slug, "spec": normalized, "engine": "deterministic-static-mvp"}, ensure_ascii=False, indent=2) + "\n",
    }
    for name, body in files.items():
        (target / name).write_text(body, encoding="utf-8")
    return {"slug": slug, "path": str(target), "files": list(ALLOWED_FILES), "preview": "static_file_only", "published": False}


def update_project(workspace: str | Path, slug: str, changes: dict[str, Any]) -> dict[str, Any]:
    """Apply a constrained brief update and regenerate only the known static files."""
    target = _project_dir(workspace, slug)
    manifest = target / "project.json"
    if not manifest.is_file() or manifest.is_symlink():
        raise WebsiteBuilderError("Projet introuvable ou manifest non sûr.")
    current = json.loads(manifest.read_text(encoding="utf-8"))
    if current.get("slug") != slug or current.get("engine") != "deterministic-static-mvp":
        raise WebsiteBuilderError("Manifest de projet invalide.")
    spec = dict(current["spec"])
    if not isinstance(changes, dict) or not changes or set(changes) - {"name", "tagline", "description", "contact"}:
        raise WebsiteBuilderError("Modifications vides ou champ non autorisé.")
    spec.update(changes)
    normalized = normalize_spec(spec)
    for name in ALLOWED_FILES:
        path = target / name
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise WebsiteBuilderError("Fichier projet non sûr.")
    (target / "index.html").write_text(_render_html(normalized), encoding="utf-8")
    (target / "project.json").write_text(
        json.dumps({"slug": slug, "spec": normalized, "engine": "deterministic-static-mvp"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"slug": slug, "updated_fields": sorted(changes), "preview": "static_file_only", "published": False}


def quality_report(workspace: str | Path, slug: str) -> dict[str, Any]:
    target = _project_dir(workspace, slug)
    html_path, css_path = target / "index.html", target / "styles.css"
    if not html_path.is_file() or not css_path.is_file():
        raise WebsiteBuilderError("Fichiers du site incomplets.")
    document = html_path.read_text(encoding="utf-8")
    stylesheet = css_path.read_text(encoding="utf-8")
    checks = {
        "html5_doctype": document.startswith("<!doctype html>"),
        "viewport": 'name="viewport"' in document,
        "language": '<html lang="fr">' in document,
        "page_title": "<title>" in document and "</title>" in document,
        "meta_description": 'name="description"' in document,
        "semantic_main": '<main id="main-content">' in document,
        "skip_navigation": 'class="skip-link"' in document,
        "visible_focus": ":focus-visible" in stylesheet,
        "responsive_tablet": "@media (max-width: 800px)" in stylesheet,
        "responsive_mobile": "@media (max-width: 520px)" in stylesheet,
        "reduced_motion": "prefers-reduced-motion: reduce" in stylesheet,
        "local_stylesheet": 'href="styles.css"' in document,
        "no_script_execution": "<script" not in document.lower(),
        "bounded_size": len(document.encode("utf-8")) <= MAX_HTML,
        "css_present": bool(stylesheet.strip()),
    }
    return {"slug": slug, "checks": checks, "passed": all(checks.values()), "preview": "static_file_only"}


def export_project(workspace: str | Path, slug: str, destination: str | Path) -> Path:
    """Create a ZIP containing only the three allowlisted regular files."""
    target = _project_dir(workspace, slug)
    report = quality_report(workspace, slug)
    if not report["passed"]:
        raise WebsiteBuilderError("Le contrôle qualité doit réussir avant export.")
    output = Path(destination).resolve()
    if output == target or target in output.parents:
        raise WebsiteBuilderError("Destination d'export dans le projet interdite.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in ALLOWED_FILES:
            path = target / name
            if path.is_symlink() or not path.is_file():
                raise WebsiteBuilderError("Fichier d'export non sûr.")
            archive.write(path, arcname=f"{slug}/{name}")
    return output
