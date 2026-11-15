"""Deterministic French child-safety screening for picture-book manuscripts."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any


class PapiKidsSafetyReviewError(ValueError):
    """Invalid manuscript or human safety-review attestation."""


_PAGE_HEADING = re.compile(
    r"^###\s+Page\s+(\d+)\s+[—-]\s+(.+?)\s*$", re.MULTILINE | re.IGNORECASE
)
_CHILD_SUBJECT = r"(?:nia|bako|les enfants|enfants|un enfant|une enfant|l'enfant|ils|elles|nous|je|tu|on)"
_RULES = (
    (
        "child_in_water",
        "critical",
        re.compile(r"\b" + _CHILD_SUBJECT + r"\s+(?:ne\s+|n['’](?:y|en)?)?(?:entre|entrent|entrait|entrait|descend|descendent|descendait|plonge|plongent|plongeait|nage|nagent|nageait|traverse|traversent|traversait|se baigne|se baignaient)\b.{0,80}\b(?:riviere|eau|ruisseau|canal)\b"),
        "Un enfant pourrait entrer dans l'eau ou la traverser.",
    ),
    (
        "drinking_unknown_water",
        "critical",
        re.compile(r"\b" + _CHILD_SUBJECT + r"\s+(?:ne\s+|n['’](?:y|en)?)?(?:boit|boivent|bois|buvons|buvez|buvait|boire|goute|goutent|goutons|goutait|avale|avalent)\b.{0,70}\b(?:eau|riviere|ruisseau|canal|mare)\b"),
        "Le texte pourrait suggérer de boire ou goûter une eau non vérifiée.",
    ),
    (
        "child_handles_hazard",
        "critical",
        re.compile(r"\b" + _CHILD_SUBJECT + r"\s+(?:ne\s+|n['’](?:y|en)?)?(?:ramasse|ramassent|ramassait|ramasser|touche|touchent|touchons|touchait|toucher|prend|prennent|prenons|prendre|ouvre|ouvrent|ouvrir|porte|portent|porter|manipule|manipulent|manipuler)\b.{0,90}\b(?:seringue|lame|verre casse|batterie|produit chimique|dechet toxique|ordure|dechet dangereux|objet coupant)\b"),
        "Un enfant pourrait manipuler un déchet ou objet dangereux.",
    ),
    (
        "unsupervised_river_or_waste",
        "high",
        re.compile(r"\b(?:seul|seule|seuls|seules|sans adulte|sans surveillance|sans accompagnement)\b.{0,80}\b(?:riviere|berge|eau|dechet|ordure|objet dangereux)\b"),
        "Une scène pourrait placer un enfant près d'un danger sans adulte.",
    ),
    (
        "child_on_unstable_bank",
        "high",
        re.compile(r"\b" + _CHILD_SUBJECT + r"\s+(?:ne\s+|n['’](?:y|en)?)?(?:glisse|glissent|glisser|court|courent|courir|grimpe|grimpent|grimper|s'approche|s'approchent|approche|approchent)\b.{0,70}\b(?:berge|bord de l'eau|rive|pente glissante)\b"),
        "Une action près d'une berge ou pente instable mérite une vérification.",
    ),
)



def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))



def _is_negated(text: str, start: int, end: int) -> bool:
    context = text[max(0, start - 20):min(len(text), end + 45)]
    has_ne = bool(re.search(r"\bne\b|\bn['’](?:y|en)?", context))
    has_negation = bool(re.search(r"\b(?:pas|jamais|plus|rien|aucun|aucune|ni)\b", context))
    return has_ne and has_negation


def analyze_child_safety(manuscript: str, *, expected_pages: int = 24) -> dict[str, Any]:
    """Flag risky phrases for human review; never auto-approve a children's manuscript."""
    if not isinstance(manuscript, str) or not manuscript.strip() or len(manuscript) > 2 * 1024 * 1024:
        raise PapiKidsSafetyReviewError("Manuscrit vide ou supérieur à 2 Mio.")
    if not isinstance(expected_pages, int) or isinstance(expected_pages, bool) or not 1 <= expected_pages <= 200:
        raise PapiKidsSafetyReviewError("Nombre de pages invalide.")
    matches = list(_PAGE_HEADING.finditer(manuscript))
    if len(matches) != expected_pages:
        raise PapiKidsSafetyReviewError(
            f"{expected_pages} pages structurées attendues ; {len(matches)} trouvées."
        )
    pages = []
    for index, match in enumerate(matches):
        page_number = int(match.group(1))
        if page_number != index + 1:
            raise PapiKidsSafetyReviewError("Les pages doivent être numérotées dans l'ordre sans doublon.")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(manuscript)
        text = manuscript[match.end():end].strip()
        normalized = _normalize(text)
        issues = []
        for rule_id, severity, pattern, description in _RULES:
            found = next(
                (candidate for candidate in pattern.finditer(normalized)
                 if not _is_negated(normalized, candidate.start(), candidate.end())),
                None,
            )
            if found:
                start = max(0, found.start() - 70)
                excerpt = re.sub(r"\s+", " ", text)[start:start + 180]
                issues.append({
                    "rule_id": rule_id,
                    "severity": severity,
                    "description": description,
                    "excerpt": excerpt,
                })
        pages.append({
            "page_number": page_number,
            "heading": match.group(2),
            "issue_count": len(issues),
            "issues": issues,
        })
    all_issues = [issue for page in pages for issue in page["issues"]]
    return {
        "schema_version": 1,
        "manuscript_sha256": hashlib.sha256(manuscript.encode("utf-8")).hexdigest(),
        "page_count": len(pages),
        "pages": pages,
        "issue_count": len(all_issues),
        "critical_issue_count": sum(1 for issue in all_issues if issue["severity"] == "critical"),
        "high_issue_count": sum(1 for issue in all_issues if issue["severity"] == "high"),
        "status": "needs_human_safety_review" if all_issues else "no_automatic_flags_human_review_still_required",
        "automatic_approval": False,
        "human_review_required": True,
    }


def attest_child_safety_review(
    analysis: dict[str, Any],
    *,
    decision: str,
    reviewer_id: str,
    reviewed_at: str,
    evidence_ref: str,
    resolution_notes: str = "",
) -> dict[str, Any]:
    """Create a human attestation tied to the exact manuscript SHA-256."""
    if not isinstance(analysis, dict) or not re.fullmatch(
        r"[0-9a-f]{64}", str(analysis.get("manuscript_sha256", ""))
    ):
        raise PapiKidsSafetyReviewError("Analyse de sécurité absente ou invalide.")
    if decision not in {"approved", "rejected"}:
        raise PapiKidsSafetyReviewError("Décision de revue invalide.")
    if not isinstance(reviewer_id, str) or not 3 <= len(reviewer_id.strip()) <= 120:
        raise PapiKidsSafetyReviewError("Identité du réviseur invalide.")
    if not isinstance(reviewed_at, str) or not reviewed_at.strip():
        raise PapiKidsSafetyReviewError("Date de revue manquante.")
    if not isinstance(evidence_ref, str) or not evidence_ref.strip():
        raise PapiKidsSafetyReviewError("Référence de preuve manquante.")
    if analysis.get("issue_count", 0) and (
        not isinstance(resolution_notes, str) or len(resolution_notes.strip()) < 20
    ):
        raise PapiKidsSafetyReviewError(
            "Une justification d'au moins 20 caractères est requise pour les alertes détectées."
        )
    return {
        "approved": decision == "approved",
        "decision": decision,
        "reviewer_id": reviewer_id.strip(),
        "reviewed_at": reviewed_at.strip(),
        "evidence_ref": evidence_ref.strip(),
        "resolution_notes": resolution_notes.strip(),
        "manuscript_sha256": analysis["manuscript_sha256"],
        "issue_count_reviewed": analysis.get("issue_count", 0),
        "critical_issue_count_reviewed": analysis.get("critical_issue_count", 0),
        "human_review": True,
    }
