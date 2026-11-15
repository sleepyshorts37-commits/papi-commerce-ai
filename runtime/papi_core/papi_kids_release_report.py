"""Compose an auditable KDP readiness report from package + human attestations."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from .papi_kids_release_gate import evaluate_kdp_release_gate

_UPLOAD_ID = re.compile(r"^PKP-UP-[0-9a-f]{32}$")


class KDPReadinessReportError(ValueError):
    """Invalid print package or manual preflight evidence."""


def _valid_attestation(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("passed") is True
        and isinstance(value.get("reviewer_id"), str)
        and 3 <= len(value["reviewer_id"]) <= 120
        and isinstance(value.get("reviewed_at"), str)
        and bool(value["reviewed_at"].strip())
        and isinstance(value.get("evidence_ref"), str)
        and bool(value["evidence_ref"].strip())
    )


def compose_kdp_readiness_report(
    *,
    book_id: str,
    private_root: str | Path,
    package_manifest: dict[str, Any],
    metadata: dict[str, Any],
    editorial_approval: dict[str, Any],
    rights: dict[str, Any],
    illustrations: list[dict[str, Any]],
    print_spec: dict[str, Any],
    kdp_account: dict[str, Any],
    pricing: dict[str, Any],
    publication_authorization: dict[str, Any],
    preflight_attestations: dict[str, Any] | None = None,
    spend_limit_minor: int = 0,
) -> dict[str, Any]:
    """Map a generated package into the release gate without inventing approvals."""
    if not isinstance(package_manifest, dict):
        raise KDPReadinessReportError("Manifeste du package KDP absent.")
    upload_id = package_manifest.get("upload_id")
    if not isinstance(upload_id, str) or not _UPLOAD_ID.fullmatch(upload_id):
        raise KDPReadinessReportError("Référence de package invalide.")
    if not isinstance(metadata, dict) or not isinstance(illustrations, list):
        raise KDPReadinessReportError("Métadonnées ou registre d'illustrations invalides.")
    package_version = package_manifest.get("package_version")
    if not isinstance(package_version, int) or isinstance(package_version, bool) or package_version < 1:
        raise KDPReadinessReportError("Version de package invalide.")

    attestations = preflight_attestations if isinstance(preflight_attestations, dict) else {}
    pdf_records: dict[str, Any] = {}
    for key in ("interior", "cover"):
        record = package_manifest.get(key)
        if not isinstance(record, dict):
            raise KDPReadinessReportError(f"Fichier PDF {key} absent du package.")
        attestation = attestations.get(key)
        preflight = "passed" if _valid_attestation(attestation) else "pending_manual_visual_inspection"
        pdf_records[key] = {
            "path": record.get("path"),
            "sha256": record.get("sha256"),
            "page_count": record.get("page_count"),
            "preflight": preflight,
        }

    try:
        page_count = int(pdf_records["interior"].get("page_count", 0))
    except (TypeError, ValueError):
        page_count = 0
    manifest = {
        "metadata": metadata,
        "editorial_approval": editorial_approval,
        "rights": rights,
        "page_count": page_count,
        "illustrations": illustrations,
        "pdfs": pdf_records,
        "print_spec": print_spec,
        "kdp_account": kdp_account,
        "pricing": pricing,
        "publication_authorization": publication_authorization,
        "spend_limit_minor": spend_limit_minor,
    }
    gate = evaluate_kdp_release_gate(
        book_id=book_id, manifest=manifest, private_root=private_root
    )
    return {
        "schema_version": 1,
        "book_id": book_id,
        "upload_id": upload_id,
        "package_version": package_version,
        "status": gate["status"],
        "publish_ready": gate["publish_ready"],
        "publication_execution_enabled": False,
        "publication_performed": False,
        "spend_limit_minor": spend_limit_minor,
        "preflight_attestations": {
            key: {
                "status": "passed" if _valid_attestation(attestations.get(key)) else "pending",
                "reviewer_id": attestations.get(key, {}).get("reviewer_id")
                    if _valid_attestation(attestations.get(key)) else None,
                "reviewed_at": attestations.get(key, {}).get("reviewed_at")
                    if _valid_attestation(attestations.get(key)) else None,
                "evidence_ref": attestations.get(key, {}).get("evidence_ref")
                    if _valid_attestation(attestations.get(key)) else None,
            }
            for key in ("interior", "cover")
        },
        "release_gate": gate,
    }


def save_kdp_readiness_report(
    private_root: str | Path,
    upload_id: str,
    report: dict[str, Any],
) -> str:
    """Persist a private JSON readiness report atomically under the book directory."""
    if not isinstance(upload_id, str) or not _UPLOAD_ID.fullmatch(upload_id):
        raise KDPReadinessReportError("Référence de dépôt invalide.")
    root = Path(private_root).resolve()
    book_dir = (root / upload_id).resolve()
    if book_dir.parent != root or not book_dir.is_dir():
        raise KDPReadinessReportError("Dossier privé du manuscrit introuvable.")
    if not isinstance(report, dict) or report.get("upload_id") != upload_id:
        raise KDPReadinessReportError("Rapport incohérent avec le dépôt.")
    target = book_dir / "kdp-readiness-report.json"
    fd, temporary = tempfile.mkstemp(prefix=".kdp-readiness-", suffix=".tmp", dir=book_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return str(target)
