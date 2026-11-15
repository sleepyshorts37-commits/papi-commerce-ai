"""Fail-closed visual quality review contract for generated book illustrations.

Technical checks are local and deterministic. Semantic visual checks are delegated
to an explicitly supplied vision reviewer; no image is approved automatically.
"""
from __future__ import annotations

from typing import Any, Callable
import hashlib


class ImageQualityError(ValueError):
    """Invalid image or malformed reviewer response."""


REQUIRED_CHECKS = (
    "prompt_adherence",
    "character_consistency",
    "style_consistency",
    "composition",
    "readability",
    "safety",
)


def _detect_image_type(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def review_generated_image(
    *,
    image_bytes: bytes,
    declared_content_type: str,
    prompt: str,
    reviewer: Callable[..., dict[str, Any]] | None,
    max_bytes: int = 25 * 1024 * 1024,
    minimum_score: float = 0.80,
) -> dict[str, Any]:
    """Run local integrity checks then request a structured semantic review.

    The reviewer must return each required check as {score: 0..1, passed: bool,
    findings: [str]}. Any missing/failed check blocks approval. This function
    never sets human_approved=True.
    """
    if not isinstance(image_bytes, bytes) or not image_bytes:
        raise ImageQualityError("Image absente ou invalide.")
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 20_000:
        raise ImageQualityError("Prompt absent ou trop long.")
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1:
        raise ImageQualityError("Limite de taille invalide.")
    if not isinstance(minimum_score, (int, float)) or isinstance(minimum_score, bool) or not 0 <= minimum_score <= 1:
        raise ImageQualityError("Seuil de score invalide.")

    detected = _detect_image_type(image_bytes)
    technical = {
        "signature_valid": detected is not None,
        "mime_matches": detected == declared_content_type,
        "size_within_limit": len(image_bytes) <= max_bytes,
    }
    technical_passed = all(technical.values())
    digest = hashlib.sha256(image_bytes).hexdigest()

    if not technical_passed:
        return {
            "status": "blocked",
            "technical_checks": technical,
            "semantic_checks": {},
            "content_sha256": digest,
            "byte_length": len(image_bytes),
            "human_approved": False,
            "approval_required": True,
            "blocking_reasons": [key for key, passed in technical.items() if not passed],
        }

    if reviewer is None:
        return {
            "status": "awaiting_visual_review",
            "technical_checks": technical,
            "semantic_checks": {},
            "content_sha256": digest,
            "byte_length": len(image_bytes),
            "human_approved": False,
            "approval_required": True,
            "blocking_reasons": ["vision_reviewer_not_configured"],
        }

    result = reviewer(image_bytes=image_bytes, content_type=detected, prompt=prompt)
    if not isinstance(result, dict):
        raise ImageQualityError("Le réviseur doit retourner un objet structuré.")
    checks = result.get("checks")
    if not isinstance(checks, dict):
        raise ImageQualityError("Réponse du réviseur sans dictionnaire checks.")

    semantic: dict[str, dict[str, Any]] = {}
    blockers: list[str] = []
    for name in REQUIRED_CHECKS:
        item = checks.get(name)
        if not isinstance(item, dict):
            blockers.append(f"missing:{name}")
            continue
        score, passed, findings = item.get("score"), item.get("passed"), item.get("findings", [])
        if (not isinstance(score, (int, float)) or isinstance(score, bool)
                or not 0 <= score <= 1 or not isinstance(passed, bool)
                or not isinstance(findings, list)
                or any(not isinstance(f, str) for f in findings)):
            raise ImageQualityError(f"Format de contrôle invalide : {name}.")
        semantic[name] = {"score": float(score), "passed": passed, "findings": findings[:20]}
        if not passed or score < minimum_score:
            blockers.append(name)

    extras = sorted(set(checks) - set(REQUIRED_CHECKS))
    if extras:
        # Unknown dimensions are retained as a warning, never trusted as gates.
        pass
    return {
        "status": "pending_human_approval" if not blockers else "blocked",
        "technical_checks": technical,
        "semantic_checks": semantic,
        "content_sha256": digest,
        "byte_length": len(image_bytes),
        "overall_score": (
            sum(item["score"] for item in semantic.values()) / len(REQUIRED_CHECKS)
            if len(semantic) == len(REQUIRED_CHECKS) else None
        ),
        "blocking_reasons": blockers,
        "reviewer_warnings": [f"unknown_check:{name}" for name in extras],
        "human_approved": False,
        "approval_required": True,
    }
