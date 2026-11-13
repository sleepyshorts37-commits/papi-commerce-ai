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
        "  <link rel=\"stylesheet\" href=\"styles.css\">\n"
        "</head>\n<body>\n<main class=\"container\">\n"
        f"  <p class=\"eyebrow\">{esc(spec['tagline'])}</p>\n"
        f"  <h1>{esc(spec['name'])}</h1>\n"
        f"  <p class=\"description\">{esc(spec['description'])}</p>\n"
        f"  <section aria-labelledby=\"contact-title\"><h2 id=\"contact-title\">Contact</h2>"
        f"<p>{esc(spec['contact'])}</p></section>\n"
        "</main>\n</body>\n</html>\n"
    )


CSS = """* { box-sizing: border-box; }
:root { color-scheme: light; font-family: system-ui, sans-serif; }
body { margin: 0; background: #f4f6f8; color: #17212b; line-height: 1.6; }
.container { width: min(100% - 2rem, 58rem); margin: 8vh auto; padding: clamp(1.5rem, 5vw, 4rem); background: white; border-radius: 1rem; }
.eyebrow { color: #2563eb; font-weight: 700; }
h1 { font-size: clamp(2rem, 7vw, 4rem); line-height: 1.1; }
.description { max-width: 65ch; }
section { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #dbe2ea; }
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
    checks = {
        "html5_doctype": document.startswith("<!doctype html>"),
        "viewport": 'name="viewport"' in document,
        "language": '<html lang="fr">' in document,
        "local_stylesheet": 'href="styles.css"' in document,
        "no_script_execution": "<script" not in document.lower(),
        "bounded_size": len(document.encode("utf-8")) <= MAX_HTML,
        "css_present": bool(css_path.read_text(encoding="utf-8").strip()),
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
