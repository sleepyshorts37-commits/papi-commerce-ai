"""PAPI KIDS asset QA and immutable audit orchestration."""
from __future__ import annotations

import hashlib
from typing import Any, Callable

from .image_asset_center import LocalImageAssetCenter
from .image_quality_audit import ImageQualityAuditLog
from .image_quality_review import review_generated_image


class PapiKidsAssetReviewError(ValueError):
    """Invalid review inputs or inconsistent stored asset."""


def review_pkp0001_assets(
    *,
    asset_center: LocalImageAssetCenter,
    audit_log: ImageQualityAuditLog,
    prompts_by_page: dict[str, str],
    reviewer: Callable[..., dict[str, Any]] | None,
    minimum_score: float = 0.80,
    max_assets: int = 24,
) -> dict[str, Any]:
    """Review pending assets and append one immutable audit event per image.

    Semantic review is optional but never silently skipped: without a reviewer,
    every valid image remains awaiting_visual_review and unapproved.
    """
    if not isinstance(prompts_by_page, dict):
        raise PapiKidsAssetReviewError("Prompts par page invalides.")
    if not isinstance(max_assets, int) or isinstance(max_assets, bool) or not 1 <= max_assets <= 24:
        raise PapiKidsAssetReviewError("Limite d'assets invalide.")
    assets = asset_center.list_assets(book_id="PKP-0001", status="pending_visual_review")
    if len(assets) > max_assets:
        raise PapiKidsAssetReviewError("Nombre d'assets supérieur à la limite de revue par exécution.")
    reports = []
    for asset in assets:
        page_id = asset.get("page_id")
        prompt = prompts_by_page.get(page_id)
        if not isinstance(prompt, str) or not prompt.strip():
            raise PapiKidsAssetReviewError(f"Prompt manquant pour {page_id}.")
        image_bytes = asset_center.read_bytes(asset)
        report = review_generated_image(
            image_bytes=image_bytes,
            declared_content_type=asset.get("mime_type", ""),
            prompt=prompt,
            reviewer=reviewer,
            minimum_score=minimum_score,
        )
        digest = asset.get("content_sha256")
        if report.get("content_sha256") != digest:
            raise PapiKidsAssetReviewError("L'empreinte du rapport ne correspond pas à l'asset.")
        event_id = "qa-" + hashlib.sha256(
            f"PKP-0001|{page_id}|{digest}".encode("utf-8")
        ).hexdigest()[:32]
        event = audit_log.append(
            event_id=event_id,
            book_id="PKP-0001",
            page_id=page_id,
            content_sha256=digest,
            report=report,
        )
        reports.append({
            "page_id": page_id,
            "content_sha256": digest,
            "status": report["status"],
            "human_approved": False,
            "audit_event_id": event["event_id"],
            "blocking_reasons": report.get("blocking_reasons", []),
        })
    return {
        "book_id": "PKP-0001",
        "reviewed_assets": len(reports),
        "pending_human_approval": sum(
            item["status"] in {"pending_human_approval", "awaiting_visual_review"}
            for item in reports
        ),
        "blocked_assets": sum(item["status"] == "blocked" for item in reports),
        "assets": reports,
        "human_approval_required": True,
        "publication_authorized": False,
    }
