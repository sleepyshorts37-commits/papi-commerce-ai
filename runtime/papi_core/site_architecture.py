"""Validated multi-page website planning contracts for PAPI WEB BUILDER.

This module creates a deterministic sitemap and requirements traceability map.
It does not generate or execute application code.
"""
from __future__ import annotations

import re
from typing import Any

SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?$")
PAGE_LIMIT = 20
REQUIREMENT_LIMIT = 100
TEXT_LIMIT = 180


class SiteArchitectureError(ValueError):
    """Raised when a website architecture brief is unsafe or inconsistent."""


def _required_text(value: Any, field: str, limit: int = TEXT_LIMIT) -> str:
    if not isinstance(value, str):
        raise SiteArchitectureError(f"{field}: texte attendu.")
    value = value.strip()
    if not value or len(value) > limit or any(ord(c) < 32 for c in value):
        raise SiteArchitectureError(f"{field}: longueur ou caractères invalides.")
    return value


def build_site_architecture(brief: dict[str, Any]) -> dict[str, Any]:
    """Validate page inventory and map each business requirement to page IDs.

    Input keys: project_name, pages[{slug,title,purpose,requirements[]}],
    requirements[{id,description,priority}].
    """
    if not isinstance(brief, dict) or set(brief) != {
        "project_name", "pages", "requirements"
    }:
        raise SiteArchitectureError("Le brief doit contenir exactement project_name, pages et requirements.")
    project_name = _required_text(brief["project_name"], "project_name")
    pages = brief["pages"]
    requirements = brief["requirements"]
    if not isinstance(pages, list) or not 1 <= len(pages) <= PAGE_LIMIT:
        raise SiteArchitectureError(f"Le site doit contenir entre 1 et {PAGE_LIMIT} pages.")
    if not isinstance(requirements, list) or len(requirements) > REQUIREMENT_LIMIT:
        raise SiteArchitectureError("Inventaire des exigences invalide ou trop volumineux.")

    requirement_map: dict[str, dict[str, str]] = {}
    for item in requirements:
        if not isinstance(item, dict) or set(item) != {"id", "description", "priority"}:
            raise SiteArchitectureError("Format d'exigence invalide.")
        identifier = item["id"]
        if not isinstance(identifier, str) or not SLUG_RE.fullmatch(identifier):
            raise SiteArchitectureError("Identifiant d'exigence invalide.")
        if identifier in requirement_map:
            raise SiteArchitectureError(f"Exigence dupliquée: {identifier}")
        priority = item["priority"]
        if priority not in {"must", "should", "could"}:
            raise SiteArchitectureError(f"Priorité invalide pour {identifier}.")
        requirement_map[identifier] = {
            "id": identifier,
            "description": _required_text(item["description"], f"{identifier}.description"),
            "priority": priority,
        }

    page_map: dict[str, dict[str, Any]] = {}
    for item in pages:
        if not isinstance(item, dict) or set(item) != {"slug", "title", "purpose", "requirements"}:
            raise SiteArchitectureError("Format de page invalide.")
        slug = item["slug"]
        if not isinstance(slug, str) or not SLUG_RE.fullmatch(slug):
            raise SiteArchitectureError("Route de page invalide.")
        if slug in page_map:
            raise SiteArchitectureError(f"Route dupliquée: {slug}")
        linked = item["requirements"]
        if not isinstance(linked, list) or not linked or len(linked) > REQUIREMENT_LIMIT:
            raise SiteArchitectureError(f"La page {slug} doit référencer au moins une exigence.")
        if len(set(linked)) != len(linked):
            raise SiteArchitectureError(f"Exigence répétée sur la page {slug}.")
        unknown = set(linked) - set(requirement_map)
        if unknown:
            raise SiteArchitectureError(f"Exigences inconnues sur {slug}: {sorted(unknown)}")
        page_map[slug] = {
            "slug": slug,
            "route": "/" if slug == "home" else f"/{slug}/",
            "file": "index.html" if slug == "home" else f"{slug}/index.html",
            "title": _required_text(item["title"], f"{slug}.title"),
            "purpose": _required_text(item["purpose"], f"{slug}.purpose"),
            "requirements": sorted(linked),
        }

    if "home" not in page_map:
        raise SiteArchitectureError("Une page home est obligatoire.")
    uncovered = set(requirement_map) - {
        requirement for page in page_map.values() for requirement in page["requirements"]
    }
    if uncovered:
        raise SiteArchitectureError(f"Exigences sans page associée: {sorted(uncovered)}")

    return {
        "project_name": project_name,
        "pages": list(page_map.values()),
        "requirements": list(requirement_map.values()),
        "traceability": {
            requirement_id: [
                page["slug"] for page in page_map.values()
                if requirement_id in page["requirements"]
            ]
            for requirement_id in sorted(requirement_map)
        },
        "status": "architecture_validated_not_generated",
    }
