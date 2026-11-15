"""Fail-closed final readiness assessment; never uploads or publishes."""
from __future__ import annotations

import re
from typing import Any


_REQUIRED_ARTIFACTS = ("interior", "cover")


def evaluate_kdp_release_gate(book_status: dict[str, Any] | None) -> dict[str, Any]:
    """Assess whether exact package artifacts have all required human approvals."""
    blockers: list[str] = []
    if not isinstance(book_status, dict):
        return _result(["Livre introuvable ou statut indisponible."])
    package = book_status.get("kdp_package_build")
    if not isinstance(package, dict):
        return _result(["Aucun package KDP fabriqué."])
    version = package.get("package_version")
    if not isinstance(version, int) or isinstance(version, bool) or not 1 <= version <= 999:
        blockers.append("Version du package invalide.")
    manifest_hash = package.get("manifest_sha256")
    if not isinstance(manifest_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", manifest_hash):
        blockers.append("Empreinte du manifeste absente ou invalide.")
    package_status = package.get("status")
    if package_status not in {
        "generated_pending_manual_pdf_inspection",
        "generated_pending_manual_multiformat_review",
        "automated_checks_passed_pending_human_review",
        "generated_pending_manual_review",
    }:
        blockers.append("Statut de fabrication non reconnu.")
    pdfs = package.get("pdfs") or {}
    reviews = book_status.get("kdp_package_reviews") or {}
    required = list(_REQUIRED_ARTIFACTS)
    ebook = package.get("ebook")
    if ebook:
        required.append("ebook")
    review_results = {}
    for artifact in required:
        record = pdfs.get(artifact) if artifact in _REQUIRED_ARTIFACTS else ebook
        if not isinstance(record, dict):
            blockers.append(f"Fichier requis absent : {artifact}.")
            continue
        digest = record.get("sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            blockers.append(f"Empreinte du fichier invalide : {artifact}.")
            continue
        review = reviews.get(f"v{version}:{artifact}")
        approved = (
            isinstance(review, dict)
            and review.get("approved") is True
            and review.get("decision") == "approved"
            and review.get("package_version") == version
            and review.get("artifact_sha256") == digest
            and isinstance(review.get("evidence_ref"), str)
            and re.fullmatch(r"[0-9a-f]{64}", review["evidence_ref"])
            and isinstance(review.get("reviewer_id"), str)
            and len(review["reviewer_id"]) >= 3
        )
        review_results[artifact] = {
            "approved": approved,
            "sha256": digest,
            "reviewer_id": review.get("reviewer_id") if isinstance(review, dict) else None,
        }
        if not approved:
            blockers.append(f"Revue humaine manquante, refusée ou périmée : {artifact}.")
    safety = book_status.get("content_safety_review")
    if not isinstance(safety, dict) or safety.get("approved") is not True:
        blockers.append("Validation humaine de sécurité jeunesse absente ou refusée.")
    metadata = book_status.get("kdp_listing_metadata")
    if (book_status.get("kdp_listing_metadata_status") != "ready_for_owner_review"
            or not isinstance(metadata, dict)
            or book_status.get("kdp_listing_metadata_blockers")):
        blockers.append("Fiche commerciale KDP incomplète ou non validée automatiquement.")
    if not isinstance(metadata, dict) or metadata.get("commercial_use_confirmed") is not True:
        blockers.append("Droits d'exploitation commerciale non confirmés.")
    return {
        "status": "ready_for_final_owner_confirmation" if not blockers else "blocked",
        "eligible_for_final_owner_confirmation": not blockers,
        "blockers": blockers,
        "package_version": version if isinstance(version, int) else None,
        "manifest_sha256": manifest_hash if isinstance(manifest_hash, str) else None,
        "artifact_reviews": review_results,
        "safety_review_approved": isinstance(safety, dict) and safety.get("approved") is True,
        "listing_metadata_validated": book_status.get("kdp_listing_metadata_status") == "ready_for_owner_review",
        "kdp_upload_enabled": False,
        "publication_performed": False,
        "spend_limit_minor": 0,
    }


def _result(blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "blocked",
        "eligible_for_final_owner_confirmation": False,
        "blockers": blockers,
        "artifact_reviews": {},
        "kdp_upload_enabled": False,
        "publication_performed": False,
        "spend_limit_minor": 0,
    }
