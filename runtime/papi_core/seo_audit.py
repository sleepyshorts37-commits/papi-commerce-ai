"""Read-only SEO diagnostics for generated static websites.

This module performs local filesystem and HTML inspection only. It makes no
network requests, does not execute page scripts, and never publishes a site.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


class SEOAuditError(ValueError):
    """Raised when the project root or its filesystem layout is unsafe."""


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.in_title = False
        self.description = ""
        self.lang = ""
        self.h1_count = 0
        self.headings: list[int] = []
        self.canonical = False
        self.og_title = False
        self.og_description = False
        self.robots = ""
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "html":
            self.lang = values.get("lang", "").strip()
        elif tag == "title":
            self.in_title = True
        elif tag == "meta":
            name = values.get("name", "").lower()
            prop = values.get("property", "").lower()
            if name == "description":
                self.description = values.get("content", "").strip()
            elif name == "robots":
                self.robots = values.get("content", "").lower()
            elif prop == "og:title":
                self.og_title = bool(values.get("content", "").strip())
            elif prop == "og:description":
                self.og_description = bool(values.get("content", "").strip())
        elif tag == "link":
            rel = {part.lower() for part in values.get("rel", "").split()}
            if "canonical" in rel and values.get("href", "").strip():
                self.canonical = True
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag[1])
            self.headings.append(level)
            if level == 1:
                self.h1_count += 1
        elif tag == "a" and values.get("href"):
            self.links.append(values["href"].strip())

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join(" ".join(self.title_parts).split())


def _safe_project_root(workspace: str | Path, slug: str) -> Path:
    if not isinstance(slug, str) or not slug or slug in {".", ".."} or "/" in slug or "\\" in slug:
        raise SEOAuditError("Identifiant de projet invalide.")
    workspace_path = Path(workspace).resolve()
    root = workspace_path / slug
    if root.is_symlink() or not root.is_dir():
        raise SEOAuditError("Dossier de projet absent ou non sûr.")
    resolved = root.resolve()
    if workspace_path not in resolved.parents:
        raise SEOAuditError("Le projet sort de l'espace de travail.")
    return resolved


def _html_pages(root: Path) -> list[Path]:
    pages: list[Path] = []
    for current, directories, filenames in __import__("os").walk(root, followlinks=False):
        current_path = Path(current)
        safe_directories = []
        for directory in directories:
            candidate = current_path / directory
            if candidate.is_symlink():
                raise SEOAuditError("Répertoire symbolique interdit dans le site.")
            safe_directories.append(directory)
        directories[:] = safe_directories
        for filename in filenames:
            candidate = current_path / filename
            if candidate.is_symlink():
                raise SEOAuditError("Fichier symbolique interdit dans le site.")
            if candidate.is_file() and candidate.suffix.lower() in {".html", ".htm"}:
                pages.append(candidate)
    return sorted(pages)


def _resolve_internal_link(page: Path, href: str, root: Path) -> Path | None:
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    if parsed.path.startswith("//"):
        return None
    target = (root / parsed.path.lstrip("/")) if parsed.path.startswith("/") else (page.parent / parsed.path)
    if parsed.path.endswith("/") or target.is_dir():
        target = target / "index.html"
    try:
        resolved = target.resolve()
    except OSError:
        return target
    if resolved != root and root not in resolved.parents:
        raise SEOAuditError("Lien interne sortant du dossier du site.")
    return resolved


def audit_static_site_seo(workspace: str | Path, slug: str) -> dict:
    """Inspect generated HTML and sitemap locally; return errors and warnings."""
    root = _safe_project_root(workspace, slug)
    pages = _html_pages(root)
    if not pages:
        raise SEOAuditError("Aucune page HTML à auditer.")

    page_reports = []
    errors: list[str] = []
    warnings: list[str] = []
    for page in pages:
        relative = page.relative_to(root).as_posix()
        parser = _PageParser()
        try:
            parser.feed(page.read_text(encoding="utf-8"))
            parser.close()
        except (UnicodeError, ValueError) as exc:
            errors.append(f"{relative}: HTML illisible ({exc}).")
            continue

        page_errors: list[str] = []
        page_warnings: list[str] = []
        title = parser.title
        if not title:
            page_errors.append("title absent.")
        elif not 30 <= len(title) <= 60:
            page_warnings.append("title hors de la plage indicative de 30 à 60 caractères.")
        if not parser.description:
            page_errors.append("meta description absente.")
        elif not 50 <= len(parser.description) <= 160:
            page_warnings.append("meta description hors de la plage indicative de 50 à 160 caractères.")
        if not parser.lang:
            page_errors.append("attribut lang absent sur html.")
        if parser.h1_count != 1:
            page_errors.append(f"la page doit contenir exactement un H1 (observé : {parser.h1_count}).")
        if parser.headings and any(
            current - previous > 1 for previous, current in zip(parser.headings, parser.headings[1:])
        ):
            page_warnings.append("saut de niveau dans la hiérarchie des titres.")
        if not parser.canonical:
            page_warnings.append("URL canonical absente ; à définir avec le domaine réel.")
        if not parser.og_title or not parser.og_description:
            page_warnings.append("métadonnées Open Graph incomplètes.")
        if "noindex" in parser.robots:
            page_warnings.append("directive robots noindex détectée.")

        for href in parser.links:
            parsed = urlsplit(href)
            if parsed.scheme.lower() == "javascript":
                page_errors.append("lien javascript: interdit.")
                continue
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            try:
                target = _resolve_internal_link(page, href, root)
            except SEOAuditError as exc:
                page_errors.append(str(exc))
                continue
            if target is not None and not target.is_file():
                page_errors.append(f"lien interne sans cible : {href}")

        errors.extend(f"{relative}: {item}" for item in page_errors)
        warnings.extend(f"{relative}: {item}" for item in page_warnings)
        page_reports.append({
            "file": relative,
            "title": title,
            "description_length": len(parser.description),
            "h1_count": parser.h1_count,
            "errors": page_errors,
            "warnings": page_warnings,
        })

    sitemap_path = root / "sitemap.xml"
    sitemap_status = "missing"
    if sitemap_path.is_symlink():
        errors.append("sitemap.xml ne doit pas être un lien symbolique.")
    elif not sitemap_path.is_file():
        warnings.append("sitemap.xml absent.")
    else:
        try:
            ET.parse(sitemap_path)
            sitemap_status = "valid_xml"
        except (ET.ParseError, OSError) as exc:
            errors.append(f"sitemap.xml invalide : {exc}")
            sitemap_status = "invalid"

    robots_path = root / "robots.txt"
    if robots_path.is_symlink():
        errors.append("robots.txt ne doit pas être un lien symbolique.")
    elif not robots_path.is_file():
        warnings.append("robots.txt absent.")

    return {
        "slug": slug,
        "page_count": len(page_reports),
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "sitemap": sitemap_status,
        "robots_txt_present": robots_path.is_file() and not robots_path.is_symlink(),
        "pages": page_reports,
        "network_requests": 0,
        "published": False,
    }
