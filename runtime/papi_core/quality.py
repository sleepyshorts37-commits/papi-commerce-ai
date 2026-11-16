"""Contrôles éditoriaux déterministes ; ne remplacent jamais une validation humaine."""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any

from .manuscript import ManuscriptError, validate_manuscript


def review_manuscript(data: dict[str, Any]) -> dict[str, Any]:
    """Produit un rapport reproductible avec blocages structurels et alertes éditoriales."""
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    try:
        report = validate_manuscript(data)
    except ManuscriptError as exc:
        return {
            "status": "blocked",
            "human_review_required": True,
            "blockers": [{"code": "STRUCTURE_INVALID", "message": str(exc)}],
            "warnings": [],
            "metrics": {},
        }

    titles = [chapter["title"].strip().casefold() for chapter in data["chapters"]]
    for title, count in Counter(titles).items():
        if count > 1:
            warnings.append({
                "code": "DUPLICATE_CHAPTER_TITLE",
                "message": f"Titre de chapitre répété ({count} fois) : {title}.",
            })

    paragraph_hashes: Counter[str] = Counter()
    for chapter in data["chapters"]:
        for paragraph in re.split(r"\n\s*\n", chapter["text"].strip()):
            normalized = re.sub(r"\s+", " ", paragraph).strip().casefold()
            if len(normalized) >= 40:
                paragraph_hashes[hashlib.sha256(normalized.encode("utf-8")).hexdigest()] += 1
    duplicates = sum(count - 1 for count in paragraph_hashes.values() if count > 1)
    if duplicates:
        warnings.append({
            "code": "REPEATED_PARAGRAPHS",
            "message": f"{duplicates} paragraphe(s) long(s) répété(s) à l'identique.",
        })

    if report.warnings:
        for warning in report.warnings:
            warnings.append({"code": "MANUSCRIPT_LENGTH", "message": warning})

    if report.word_count < 250:
        warnings.append({
            "code": "SHORT_MANUSCRIPT",
            "message": "Manuscrit court : confirmer que la longueur correspond au format éditorial choisi.",
        })

    return {
        "status": "requires_human_review",
        "human_review_required": True,
        "blockers": blockers,
        "warnings": warnings,
        "metrics": {
            "title": report.title,
            "language": report.language,
            "age_range": report.age_range,
            "chapter_count": report.chapter_count,
            "word_count": report.word_count,
            "content_sha256": report.content_sha256,
            "duplicate_long_paragraphs": duplicates,
        },
        "limitations": [
            "Aucune détection sémantique fiable du plagiat ou des droits n'est effectuée.",
            "La qualité narrative, l'adéquation réelle à l'âge et l'exactitude pédagogique exigent une revue humaine.",
            "Ce rapport n'est pas une approbation éditoriale ni une autorisation de publication.",
        ],
    }
