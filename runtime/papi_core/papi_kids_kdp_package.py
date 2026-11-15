"""Atomic orchestration of the KDP paperback interior and full-wrap cover PDFs."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any

from .papi_kids_kdp_preflight import KDPPreflightError
from .papi_kids_cover_pdf import KDPCoverError, build_kdp_cover_pdf
from .papi_kids_kdp_preflight import build_interior_pdf


class PapiKidsKDPPrintPackageError(ValueError):
    """Paperback package inputs or output failed validation."""


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
    """Build both PDFs as one atomic package; only approved art and official KDP template."""
    if not isinstance(upload_id, str) or not re.fullmatch(r"PKP-UP-[0-9a-f]{32}", upload_id):
        raise PapiKidsKDPPrintPackageError("Référence de dépôt invalide.")
    if not isinstance(package_version, int) or isinstance(package_version, bool) or not 1 <= package_version <= 999:
        raise PapiKidsKDPPrintPackageError("Version de package invalide.")
    if not isinstance(interior_args, dict) or not isinstance(cover_args, dict):
        raise PapiKidsKDPPrintPackageError("Paramètres intérieurs/couverture invalides.")
    controlled = {"storage_root", "output_path", "upload_id"}
    if controlled.intersection(interior_args) or controlled.intersection(cover_args):
        raise PapiKidsKDPPrintPackageError("Les chemins et identifiants sont contrôlés par le service.")
    root = Path(storage_root).resolve()
    book_dir = (root / upload_id).resolve()
    if book_dir.parent != root or not book_dir.is_dir():
        raise PapiKidsKDPPrintPackageError("Dossier privé du manuscrit introuvable.")
    pages = interior_args.get("pages")
    assets = interior_args.get("assets")
    if not isinstance(pages, list) or not isinstance(assets, list) or len(pages) < 24 or len(pages) % 2:
        raise PapiKidsKDPPrintPackageError("Pagination imprimée paire de 24 pages minimum requise.")
    page_count = len(pages)
    if len(assets) != page_count:
        raise PapiKidsKDPPrintPackageError("Une illustration approuvée est requise pour chaque page.")
    page_numbers = [asset.get("page_number") if isinstance(asset, dict) else None for asset in assets]
    if (any(not isinstance(number, int) or isinstance(number, bool) for number in page_numbers)
            or sorted(page_numbers) != list(range(1, page_count + 1))):
        raise PapiKidsKDPPrintPackageError("Les illustrations ne couvrent pas exactement toutes les pages.")
    if any(asset.get("review_status") != "approved" for asset in assets):
        raise PapiKidsKDPPrintPackageError("Toutes les illustrations intérieures doivent être approuvées.")
    if cover_args.get("page_count") != page_count:
        raise PapiKidsKDPPrintPackageError("La pagination de couverture diffère de l'intérieur.")
    for dimension in ("trim_width_in", "trim_height_in"):
        if float(cover_args.get(dimension, 0)) != float(interior_args.get(dimension, 0)):
            raise PapiKidsKDPPrintPackageError("Le format de coupe de la couverture et de l'intérieur diffère.")
    for field in ("front_asset", "back_asset"):
        asset = cover_args.get(field)
        if not isinstance(asset, dict) or asset.get("review_status") != "approved":
            raise PapiKidsKDPPrintPackageError(f"Illustration de couverture {field} non approuvée.")
    template = cover_args.get("cover_template")
    if not isinstance(template, dict):
        raise PapiKidsKDPPrintPackageError("Gabarit officiel KDP manquant.")
    template_path_value = template.get("template_path")
    if not isinstance(template_path_value, str):
        raise PapiKidsKDPPrintPackageError("Chemin du gabarit KDP invalide.")
    template_path = Path(template_path_value).resolve()
    if root not in template_path.parents or not template_path.is_file():
        raise PapiKidsKDPPrintPackageError("Le gabarit KDP doit être conservé dans le stockage privé du livre.")
    if _sha256(template_path) != template.get("template_sha256"):
        raise PapiKidsKDPPrintPackageError("Empreinte du gabarit KDP incorrecte.")
    if not str(template.get("source_url", "")).startswith("https://kdp.amazon.com/") or not template.get("downloaded_at"):
        raise PapiKidsKDPPrintPackageError("Source officielle et date du gabarit KDP obligatoires.")

    final_dir = book_dir / f"kdp-print-package-v{package_version:03d}"
    if final_dir.exists():
        raise PapiKidsKDPPrintPackageError("Cette version du package imprimé existe déjà.")
    stage = Path(tempfile.mkdtemp(prefix=".kdp-print-package-", dir=book_dir))
    os.chmod(stage, 0o700)
    interior_path = stage / "interior.pdf"
    cover_path = stage / "cover.pdf"
    try:
        interior_result = build_interior_pdf(
            root, interior_path, upload_id=upload_id, **interior_args
        )
        cover_result = build_kdp_cover_pdf(
            root, cover_path, **cover_args
        )
        for path, label in ((interior_path, "intérieur"), (cover_path, "couverture")):
            if not path.is_file() or not path.read_bytes().startswith(b"%PDF-"):
                raise PapiKidsKDPPrintPackageError(f"PDF {label} absent ou invalide.")
        if interior_result.get("page_count") != page_count or cover_result.get("page_count") != 1:
            raise PapiKidsKDPPrintPackageError("Pagination des PDF produite incorrecte.")
        interior_sha = _sha256(interior_path)
        cover_sha = _sha256(cover_path)
        manifest = {
            "schema_version": 1,
            "upload_id": upload_id,
            "package_version": package_version,
            "page_count": page_count,
            "pdfs": {
                "interior": {
                    "path": f"{upload_id}/kdp-print-package-v{package_version:03d}/interior.pdf",
                    "sha256": interior_sha,
                    "page_count": page_count,
                    "preflight": "pending_manual_pdf_inspection",
                },
                "cover": {
                    "path": f"{upload_id}/kdp-print-package-v{package_version:03d}/cover.pdf",
                    "sha256": cover_sha,
                    "page_count": 1,
                    "preflight": "pending_manual_pdf_inspection",
                },
            },
            "print_spec": {
                "trim_size": f"{cover_args['trim_width_in']}x{cover_args['trim_height_in']}",
                "paper_type": cover_args["paper_type"],
                "color_mode": interior_args["color_mode"],
                "bleed": interior_args["bleed"],
                "cover_template_sha256": template["template_sha256"],
            },
            "human_approval_required": True,
            "spend_limit_minor": 0,
            "kdp_upload_ready": False,
            "publication_performed": False,
        }
        manifest_path = stage / "package-manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(manifest_path, 0o600)
        os.replace(stage, final_dir)
    except Exception as exc:
        shutil.rmtree(stage, ignore_errors=True)
        if isinstance(exc, (PapiKidsKDPPrintPackageError, KDPPreflightError, KDPCoverError)):
            raise
        raise PapiKidsKDPPrintPackageError("La fabrication du package broché a échoué.") from exc
    return {
        "package_dir": str(final_dir),
        "manifest_path": str(final_dir / "package-manifest.json"),
        "manifest": manifest,
        "interior_result": {**interior_result, "output_path": str(final_dir / "interior.pdf")},
        "cover_result": {**cover_result, "output_path": str(final_dir / "cover.pdf")},
        "status": "generated_pending_manual_pdf_inspection",
        "kdp_upload_ready": False,
        "publication_performed": False,
        "spend_limit_minor": 0,
    }
