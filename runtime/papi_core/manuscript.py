"""Validation éditoriale structurelle et assemblage Markdown des manuscrits."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any


class ManuscriptError(ValueError):
    """Manuscrit incomplet ou structurellement invalide."""


@dataclass(frozen=True)
class ManuscriptReport:
    title: str
    language: str
    age_range: str
    chapter_count: int
    word_count: int
    content_sha256: str
    warnings: tuple[str, ...]


def _required_text(value: Any, field: str, limit: int = 20000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManuscriptError(f"Champ obligatoire absent ou vide : {field}.")
    value = value.strip()
    if len(value) > limit:
        raise ManuscriptError(f"Champ trop long : {field}.")
    return value


def validate_manuscript(data: dict[str, Any]) -> ManuscriptReport:
    """Vérifie la structure et les placeholders ; ne remplace pas une revue humaine."""
    if not isinstance(data, dict):
        raise ManuscriptError("Le manuscrit doit être un objet structuré.")
    title = _required_text(data.get("title"), "title", 300)
    language = _required_text(data.get("language"), "language", 12).lower()
    if language not in {"fr", "en"}:
        raise ManuscriptError("Langue non prise en charge par le validateur : fr ou en.")
    age_range = _required_text(data.get("age_range"), "age_range", 20)
    if not re.fullmatch(r"\d{1,2}-\d{1,2}", age_range):
        raise ManuscriptError("Tranche d'âge attendue au format 6-9.")
    low, high = (int(part) for part in age_range.split("-"))
    if low < 2 or high > 18 or low > high:
        raise ManuscriptError("Tranche d'âge incohérente.")
    synopsis = _required_text(data.get("synopsis"), "synopsis", 5000)
    chapters = data.get("chapters")
    if not isinstance(chapters, list) or not 1 <= len(chapters) <= 80:
        raise ManuscriptError("Le manuscrit doit contenir entre 1 et 80 chapitres.")
    pieces = [title, synopsis]
    words = len(re.findall(r"\b[\w’'-]+\b", synopsis, re.UNICODE))
    warnings: list[str] = []
    for index, chapter in enumerate(chapters, 1):
        if not isinstance(chapter, dict):
            raise ManuscriptError(f"Chapitre {index} invalide.")
        chapter_title = _required_text(chapter.get("title"), f"chapters[{index}].title", 300)
        body = _required_text(chapter.get("text"), f"chapters[{index}].text", 30000)
        if len(body) < 80:
            warnings.append(f"Chapitre {index} très court : revue éditoriale nécessaire.")
        illustration = chapter.get("illustration_brief", "")
        if illustration and (not isinstance(illustration, str) or len(illustration) > 3000):
            raise ManuscriptError(f"Brief d'illustration invalide au chapitre {index}.")
        pieces.extend([chapter_title, body, illustration])
        words += len(re.findall(r"\b[\w’'-]+\b", chapter_title + " " + body, re.UNICODE))
    complete_text = "\n".join(pieces)
    if re.search(r"\b(TODO|TBD|PLACEHOLDER|INSERT HERE|À COMPLÉTER|À REMPLACER)\b", complete_text, re.I):
        raise ManuscriptError("Le manuscrit contient un marqueur de contenu provisoire.")
    if words < 100:
        warnings.append("Manuscrit très court : confirmer le format éditorial attendu.")
    digest = hashlib.sha256(complete_text.encode("utf-8")).hexdigest()
    return ManuscriptReport(
        title=title, language=language, age_range=age_range,
        chapter_count=len(chapters), word_count=words,
        content_sha256=digest, warnings=tuple(warnings),
    )


def render_manuscript_markdown(data: dict[str, Any]) -> str:
    """Assemble un manuscrit validé en Markdown ; ne génère ni PDF ni EPUB."""
    validate_manuscript(data)
    lines = [
        f"# {data['title'].strip()}",
        "",
        f"**Langue :** {data['language']}  ",
        f"**Âge cible :** {data['age_range']} ans",
        "",
        "## Synopsis",
        "",
        data["synopsis"].strip(),
    ]
    for index, chapter in enumerate(data["chapters"], 1):
        lines.extend(["", f"## {index}. {chapter['title'].strip()}", "", chapter["text"].strip()])
        brief = chapter.get("illustration_brief", "")
        if brief:
            lines.extend(["", f"> **Brief illustration :** {brief.strip()}"])
    return "\n".join(lines) + "\n"
