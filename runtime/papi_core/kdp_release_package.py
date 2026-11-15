"""Human-gated KDP candidate package builder; never uploads or publishes."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
import re
import zipfile
from typing import Any


class KDPReleaseGateError(ValueError):
    """Release evidence is incomplete or a candidate package is unsafe."""


def build_kdp_candidate_package(
    *,
    interior_pdf: bytes,
    cover_pdf: bytes,
    metadata: dict[str, Any],
    asset_reviews: list[dict[str, Any]],
    editorial_approval: dict[str, Any],
    rights_evidence: dict[str, Any],
    preflight_report: dict[str, Any],
) -> dict[str, Any]:
    """Build a ZIP candidate only after all mandatory human gates pass."""
    if not isinstance(interior_pdf, bytes) or not interior_pdf.startswith(b"%PDF-"):
        raise KDPReleaseGateError("PDF intérieur absent ou signature PDF invalide.")
    if not isinstance(cover_pdf, bytes) or not cover_pdf.startswith(b"%PDF-"):
        raise KDPReleaseGateError("PDF couverture absent ou signature PDF invalide.")
    if not isinstance(metadata, dict):
        raise KDPReleaseGateError("Métadonnées éditoriales obligatoires.")
    required_metadata = ("title", "language", "author", "trim_size", "price", "territories")
    missing = [key for key in required_metadata if not metadata.get(key)]
    if missing:
        raise KDPReleaseGateError("Métadonnées KDP à confirmer : " + ", ".join(missing))
    if metadata["title"] != "Nia et la rivière aux mille reflets":
        raise KDPReleaseGateError("Le titre ne correspond pas au livre pilote PKP-0001.")
    if not isinstance(asset_reviews, list) or len(asset_reviews) != 24:
        raise KDPReleaseGateError("24 validations humaines d'illustrations sont obligatoires.")
    for index, review in enumerate(asset_reviews):
        if not isinstance(review, dict) or review.get("decision") != "approved" or not review.get("reviewer_id"):
            raise KDPReleaseGateError(f"Approbation humaine absente pour l'illustration {index + 1}.")
        if not re.fullmatch(r"[a-f0-9]{64}", str(review.get("content_sha256", ""))):
            raise KDPReleaseGateError(f"Empreinte SHA-256 manquante pour l'illustration {index + 1}.")
    if (not isinstance(editorial_approval, dict)
            or editorial_approval.get("approved") is not True
            or not editorial_approval.get("reviewer_id")
            or not editorial_approval.get("manuscript_sha256")):
        raise KDPReleaseGateError("Validation éditoriale indépendante et propriétaire absentes.")
    if (not isinstance(rights_evidence, dict)
            or rights_evidence.get("commercial_use") is not True
            or rights_evidence.get("print_on_demand") is not True
            or not rights_evidence.get("evidence_ref")):
        raise KDPReleaseGateError("Droits commerciaux et impression à la demande non démontrés.")
    if (not isinstance(preflight_report, dict)
            or preflight_report.get("status") != "ready_for_human_review"
            or preflight_report.get("kdp_upload_authorized") is not False):
        raise KDPReleaseGateError("Préflight technique non conforme ou rapport invalide.")

    hashes = {
        "interior.pdf": hashlib.sha256(interior_pdf).hexdigest(),
        "cover.pdf": hashlib.sha256(cover_pdf).hexdigest(),
    }
    manifest = {
        "schema_version": 1,
        "book_id": "PKP-0001",
        "title": metadata["title"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": hashes,
        "human_gates": {
            "illustrations_approved": 24,
            "editorial_approved": True,
            "commercial_rights_verified": True,
            "print_preflight_passed": True,
        },
        "publication_status": "candidate_ready_for_owner_review",
        "kdp_upload_performed": False,
        "publication_authorized": False,
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("interior.pdf", interior_pdf)
        archive.writestr("cover.pdf", cover_pdf)
        archive.writestr("release-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return {
        "status": "candidate_ready_for_owner_review",
        "package_zip": buffer.getvalue(),
        "manifest": manifest,
        "package_sha256": hashlib.sha256(buffer.getvalue()).hexdigest(),
        "kdp_upload_performed": False,
        "publication_authorized": False,
    }
