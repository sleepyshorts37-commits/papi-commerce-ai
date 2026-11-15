"""Atomic offline assembly of the two separate KDP print PDFs."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

from .papi_kids_kdp_preflight import build_interior_pdf
from .papi_kids_kdp_cover import build_kdp_full_wrap_cover_pdf

_UPLOAD_ID_PREFIX = "PKP-UP-"


class KDPPrintPackageError(ValueError):
    """The requested print package could not be built safely."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_kdp_print_package(
    *,
    storage_root: str | Path,
    upload_id: str,
    interior_args: dict[str, Any],
    cover_args: dict[str, Any],
    package_version: int = 1,
) -> dict[str, Any]:
    """Build interior + cover in a private staging directory and publish atomically.

    This creates files only. It never marks preflight as passed, never authorizes
    KDP submission, and never uploads or publishes the book.
    """
    if not isinstance(upload_id, str) or not upload_id.startswith(_UPLOAD_ID_PREFIX) or len(upload_id) != 39:
        raise KDPPrintPackageError("Référence de dépôt invalide.")
    if not isinstance(package_version, int) or isinstance(package_version, bool) or not 1 <= package_version <= 999:
        raise KDPPrintPackageError("Version de dossier invalide.")
    if not isinstance(interior_args, dict) or not isinstance(cover_args, dict):
        raise KDPPrintPackageError("Paramètres de fabrication invalides.")
    forbidden = {"storage_root", "output_path", "upload_id"}
    if forbidden.intersection(interior_args) or forbidden.intersection(cover_args):
        raise KDPPrintPackageError("Les chemins de sortie et références sont contrôlés par le service.")
    root = Path(storage_root).resolve()
    book_dir = (root / upload_id).resolve()
    if book_dir.parent != root or not book_dir.is_dir():
        raise KDPPrintPackageError("Dossier privé du manuscrit introuvable.")
    final_dir = book_dir / f"kdp-package-v{package_version:03d}"
    if final_dir.exists():
        raise KDPPrintPackageError("Cette version de dossier KDP existe déjà.")

    stage_dir = Path(tempfile.mkdtemp(prefix=".kdp-package-", dir=book_dir))
    os.chmod(stage_dir, 0o700)
    interior_path = stage_dir / "interior.pdf"
    cover_path = stage_dir / "cover.pdf"
    try:
        interior = build_interior_pdf(
            root, interior_path, upload_id=upload_id, **interior_args
        )
        cover = build_kdp_full_wrap_cover_pdf(
            root, cover_path, upload_id=upload_id, **cover_args
        )
        interior_bytes = interior_path.read_bytes()
        cover_bytes = cover_path.read_bytes()
        if not interior_bytes.startswith(b"%PDF-") or not cover_bytes.startswith(b"%PDF-"):
            raise KDPPrintPackageError("L'un des rendus n'est pas un PDF valide.")
        package_manifest = {
            "schema_version": 1,
            "upload_id": upload_id,
            "package_version": package_version,
            "interior": {
                "path": f"{upload_id}/kdp-package-v{package_version:03d}/interior.pdf",
                "sha256": _sha256(interior_path),
                "page_count": interior["page_count"],
                "preflight": "pending_manual_visual_inspection",
            },
            "cover": {
                "path": f"{upload_id}/kdp-package-v{package_version:03d}/cover.pdf",
                "sha256": _sha256(cover_path),
                "page_count": 1,
                "template_sha256": cover["template_sha256"],
                "preflight": "pending_manual_visual_inspection",
            },
            "human_approval_required": True,
            "kdp_submission_ready": False,
            "upload_or_publication_performed": False,
            "spend_limit_minor": 0,
        }
        manifest_path = stage_dir / "package-manifest.json"
        manifest_path.write_text(
            json.dumps(package_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.chmod(manifest_path, 0o600)
        os.replace(stage_dir, final_dir)
    except Exception:
        shutil.rmtree(stage_dir, ignore_errors=True)
        raise
    return {
        "package_dir": str(final_dir),
        "manifest": package_manifest,
        "interior": interior,
        "cover": cover,
        "status": "generated_pending_manual_inspection",
        "kdp_submission_ready": False,
        "publication_performed": False,
        "spend_limit_minor": 0,
    }
