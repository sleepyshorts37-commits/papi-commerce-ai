"""Controlled bridge between commercial copy drafts and static PAPI websites.

The bridge is local-only: it makes no network calls and never publishes a site.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from papi_core.content_generation import generate_commercial_content
from papi_core.website_builder import generate_project, quality_report


class CommercialSiteError(ValueError):
    """Raised when a commercial draft cannot safely fit a website brief."""


def generate_commercial_site(
    workspace: str | Path, slug: str, brief: dict[str, Any]
) -> dict[str, Any]:
    """Generate a review-required one-page website from a validated content brief.

    The full generated body and sector disclaimer are placed in the site description.
    Oversized content is rejected rather than silently truncated by the website builder.
    """
    content = generate_commercial_content(brief)
    description = f"{content['body']}\n\n{content['disclaimer']}"
    if len(description) > 1000:
        raise CommercialSiteError(
            "Le contenu dépasse 1 000 caractères ; réduisez les faits du brief."
        )

    site = generate_project(
        workspace,
        slug,
        {
            "name": brief["brand"],
            "tagline": brief["offer"],
            "description": description,
            "contact": content["cta"] or brief.get(
                "cta", "Contactez-nous pour en savoir plus."
            ),
        },
    )
    quality = quality_report(workspace, slug)
    return {
        "slug": site["slug"],
        "path": site["path"],
        "files": site["files"],
        "quality": quality,
        "commercial_content": content,
        "review_required": True,
        "published": False,
        "network_used": False,
    }
