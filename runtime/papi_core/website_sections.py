"""Strict, reusable content sections for safe multi-page website generation."""
from __future__ import annotations

import html
import re
from typing import Any

SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?$")
SECTION_TYPES = {"intro", "feature_grid", "stats", "faq", "cta", "product_catalog", "team", "testimonials", "service_cards"}
MAX_SECTIONS_PER_PAGE = 8


class WebsiteSectionError(ValueError):
    """Raised for invalid or unsafe website section content."""


def _text(value: Any, field: str, limit: int = 220) -> str:
    if not isinstance(value, str):
        raise WebsiteSectionError(f"{field}: texte attendu.")
    value = value.strip()
    if not value or len(value) > limit or any(ord(char) < 32 for char in value):
        raise WebsiteSectionError(f"{field}: longueur ou caractères invalides.")
    return value


def _items(value: Any, field: str, minimum: int, maximum: int) -> list[dict[str, str]]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise WebsiteSectionError(f"{field}: nombre d'éléments invalide.")
    return value


def render_page_sections(
    sections: Any, current_slug: str, page_slugs: set[str]
) -> str:
    """Validate and render a small allowlisted vocabulary of semantic sections.

    Only internal CTA destinations are accepted. No raw HTML, scripts, styles,
    arbitrary URLs, or user-defined CSS can enter the generated document.
    """
    if not isinstance(sections, list) or len(sections) > MAX_SECTIONS_PER_PAGE:
        raise WebsiteSectionError("La liste de sections est invalide ou trop longue.")
    rendered: list[str] = []
    identifiers: set[str] = set()

    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            raise WebsiteSectionError("Chaque section doit être un objet.")
        kind = section.get("type")
        if not isinstance(kind, str) or kind not in SECTION_TYPES:
            raise WebsiteSectionError("Type de section non autorisé.")
        identifier = section.get("id")
        if not isinstance(identifier, str) or not SLUG_RE.fullmatch(identifier) or identifier in identifiers:
            raise WebsiteSectionError("Identifiant de section invalide ou dupliqué.")
        identifiers.add(identifier)
        heading = html.escape(_text(section.get("heading"), f"{identifier}.heading"))
        eyebrow = html.escape(_text(section.get("eyebrow", "Découvrir"), f"{identifier}.eyebrow", 80))
        body_value = section.get("body")
        body = html.escape(_text(body_value, f"{identifier}.body", 1000)) if body_value is not None else ""
        heading_id = f"section-{identifier}"

        if kind == "intro":
            allowed = {"id", "type", "eyebrow", "heading", "body"}
            if set(section) != allowed or not body:
                raise WebsiteSectionError("Section intro : champs requis ou supplémentaires invalides.")
            rendered.append(f'<section class="content-section content-intro" aria-labelledby="{heading_id}"><p class="eyebrow">{eyebrow}</p><h2 id="{heading_id}">{heading}</h2><p>{body}</p></section>')

        elif kind == "feature_grid":
            allowed = {"id", "type", "eyebrow", "heading", "body", "items"}
            if set(section) != allowed:
                raise WebsiteSectionError("Section feature_grid : champs invalides.")
            cards = []
            for item in _items(section["items"], f"{identifier}.items", 2, 6):
                if not isinstance(item, dict) or set(item) != {"title", "body"}:
                    raise WebsiteSectionError("Carte de fonctionnalité invalide.")
                cards.append(f'<article class="feature-card"><h3>{html.escape(_text(item["title"], "card.title"))}</h3><p>{html.escape(_text(item["body"], "card.body", 500))}</p></article>')
            body_html = f"<p>{body}</p>" if body else ""
            rendered.append(f'<section class="content-section" aria-labelledby="{heading_id}"><p class="eyebrow">{eyebrow}</p><h2 id="{heading_id}">{heading}</h2>{body_html}<div class="feature-grid">{"".join(cards)}</div></section>')

        elif kind == "stats":
            allowed = {"id", "type", "eyebrow", "heading", "body", "items"}
            if set(section) != allowed:
                raise WebsiteSectionError("Section stats : champs invalides.")
            stats = []
            for item in _items(section["items"], f"{identifier}.items", 2, 4):
                if not isinstance(item, dict) or set(item) != {"value", "label"}:
                    raise WebsiteSectionError("Indicateur invalide.")
                stats.append(f'<div class="stat-card"><strong>{html.escape(_text(item["value"], "stat.value", 40))}</strong><span>{html.escape(_text(item["label"], "stat.label", 100))}</span></div>')
            body_html = f"<p>{body}</p>" if body else ""
            rendered.append(f'<section class="content-section" aria-labelledby="{heading_id}"><p class="eyebrow">{eyebrow}</p><h2 id="{heading_id}">{heading}</h2>{body_html}<div class="stats-grid">{"".join(stats)}</div></section>')

        elif kind == "faq":
            allowed = {"id", "type", "eyebrow", "heading", "body", "items"}
            if set(section) != allowed:
                raise WebsiteSectionError("Section faq : champs invalides.")
            questions = []
            for item in _items(section["items"], f"{identifier}.items", 1, 8):
                if not isinstance(item, dict) or set(item) != {"question", "answer"}:
                    raise WebsiteSectionError("Entrée FAQ invalide.")
                question = html.escape(_text(item["question"], "faq.question"))
                answer = html.escape(_text(item["answer"], "faq.answer", 1000))
                questions.append(f"<details><summary>{question}</summary><p>{answer}</p></details>")
            body_html = f"<p>{body}</p>" if body else ""
            rendered.append(f'<section class="content-section faq-section" aria-labelledby="{heading_id}"><p class="eyebrow">{eyebrow}</p><h2 id="{heading_id}">{heading}</h2>{body_html}{"".join(questions)}</section>')

        elif kind == "product_catalog":
            allowed = {"id", "type", "eyebrow", "heading", "body", "items"}
            if set(section) != allowed:
                raise WebsiteSectionError("Section product_catalog : champs invalides.")
            cards = []
            for item in _items(section["items"], f"{identifier}.items", 1, 12):
                if not isinstance(item, dict) or set(item) != {"name", "description", "price_label", "cta_label", "target_page"}:
                    raise WebsiteSectionError("Fiche produit invalide.")
                target = item["target_page"]
                if not isinstance(target, str) or target not in page_slugs:
                    raise WebsiteSectionError("La destination produit doit être une page interne existante.")
                href = ("index.html" if target == "home" else f"{target}/index.html") if current_slug == "home" else ("../index.html" if target == "home" else f"../{target}/index.html")
                cards.append(f'<article class="product-card"><h3>{html.escape(_text(item["name"], "product.name"))}</h3><p>{html.escape(_text(item["description"], "product.description", 500))}</p><p class="product-price">{html.escape(_text(item["price_label"], "product.price_label", 80))}</p><a class="primary-link" href="{href}">{html.escape(_text(item["cta_label"], "product.cta_label", 80))}</a></article>')
            rendered.append(f'<section class="content-section product-catalog" aria-labelledby="{heading_id}"><p class="eyebrow">{eyebrow}</p><h2 id="{heading_id}">{heading}</h2>{f"<p>{body}</p>" if body else ""}<div class="business-grid">{"".join(cards)}</div></section>')

        elif kind == "team":
            allowed = {"id", "type", "eyebrow", "heading", "body", "items"}
            if set(section) != allowed:
                raise WebsiteSectionError("Section team : champs invalides.")
            cards = []
            for item in _items(section["items"], f"{identifier}.items", 1, 12):
                if not isinstance(item, dict) or set(item) != {"name", "role", "bio"}:
                    raise WebsiteSectionError("Fiche membre invalide.")
                cards.append(f'<article class="team-card"><h3>{html.escape(_text(item["name"], "team.name"))}</h3><p class="team-role">{html.escape(_text(item["role"], "team.role", 100))}</p><p>{html.escape(_text(item["bio"], "team.bio", 500))}</p></article>')
            rendered.append(f'<section class="content-section team-section" aria-labelledby="{heading_id}"><p class="eyebrow">{eyebrow}</p><h2 id="{heading_id}">{heading}</h2>{f"<p>{body}</p>" if body else ""}<div class="business-grid">{"".join(cards)}</div></section>')

        elif kind == "testimonials":
            allowed = {"id", "type", "eyebrow", "heading", "body", "items"}
            if set(section) != allowed:
                raise WebsiteSectionError("Section testimonials : champs invalides.")
            cards = []
            for item in _items(section["items"], f"{identifier}.items", 1, 8):
                if not isinstance(item, dict) or set(item) != {"quote", "author", "role"}:
                    raise WebsiteSectionError("Témoignage invalide.")
                cards.append(f'<figure class="testimonial-card"><blockquote>{html.escape(_text(item["quote"], "testimonial.quote", 700))}</blockquote><figcaption><strong>{html.escape(_text(item["author"], "testimonial.author"))}</strong><span>{html.escape(_text(item["role"], "testimonial.role", 100))}</span></figcaption></figure>')
            rendered.append(f'<section class="content-section testimonials-section" aria-labelledby="{heading_id}"><p class="eyebrow">{eyebrow}</p><h2 id="{heading_id}">{heading}</h2>{f"<p>{body}</p>" if body else ""}<p class="content-disclaimer">Témoignages fournis par le client ; leur authenticité n’a pas été vérifiée.</p><div class="business-grid">{"".join(cards)}</div></section>')

        elif kind == "service_cards":
            allowed = {"id", "type", "eyebrow", "heading", "body", "items"}
            if set(section) != allowed:
                raise WebsiteSectionError("Section service_cards : champs invalides.")
            cards = []
            for item in _items(section["items"], f"{identifier}.items", 1, 8):
                if not isinstance(item, dict) or set(item) != {"title", "body"}:
                    raise WebsiteSectionError("Carte de service invalide.")
                cards.append(f'<article class="service-card"><h3>{html.escape(_text(item["title"], "service.title"))}</h3><p>{html.escape(_text(item["body"], "service.body", 500))}</p></article>')
            rendered.append(f'<section class="content-section service-section" aria-labelledby="{heading_id}"><p class="eyebrow">{eyebrow}</p><h2 id="{heading_id}">{heading}</h2>{f"<p>{body}</p>" if body else ""}<div class="business-grid">{"".join(cards)}</div></section>')

        else:  # cta
            allowed = {"id", "type", "eyebrow", "heading", "body", "cta_label", "target_page"}
            if set(section) != allowed:
                raise WebsiteSectionError("Section cta : champs invalides.")
            target = section["target_page"]
            if not isinstance(target, str) or target not in page_slugs:
                raise WebsiteSectionError("La destination CTA doit être une page interne existante.")
            label = html.escape(_text(section["cta_label"], "cta_label", 80))
            href = ("index.html" if target == "home" else f"{target}/index.html") if current_slug == "home" else ("../index.html" if target == "home" else f"../{target}/index.html")
            body_html = f"<p>{body}</p>" if body else ""
            rendered.append(f'<section class="content-section section-cta" aria-labelledby="{heading_id}"><p class="eyebrow">{eyebrow}</p><h2 id="{heading_id}">{heading}</h2>{body_html}<a class="primary-link" href="{href}">{label}</a></section>')

    return "\n".join(rendered)
