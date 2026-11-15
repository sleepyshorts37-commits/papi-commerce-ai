"""Strict final release gate for Amazon KDP; never uploads or publishes."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
from typing import Any

from .papi_kids_print_resolution import PrintResolutionError, audit_image_resolution
from .papi_kids_ebook_package import PapiKidsEPUBPackageError, validate_epub_structure
from .papi_kids_kdp_metadata import validate_kdp_listing_metadata

_BOOK_ID = re.compile(r"^PKP-[0-9]{4,8}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _missing(condition: bool, message: str, blockers: list[str]) -> None:
    if not condition:
        blockers.append(message)


def evaluate_kdp_release_gate(
    *,
    book_id: str,
    manifest: dict[str, Any],
    private_root: str | Path,
) -> dict[str, Any]:
    """Evaluate every human, rights, print, commercial and account prerequisite."""
    blockers: list[str] = []
    if not isinstance(book_id, str) or not _BOOK_ID.fullmatch(book_id):
        blockers.append("Identifiant du livre invalide.")
    if not isinstance(manifest, dict):
        return {
            "book_id": book_id, "status": "blocked", "publish_ready": False,
            "publication_execution_enabled": False,
            "blockers": ["Manifeste de publication absent ou invalide."],
        }

    metadata = manifest.get("metadata") or {}
    listing_metadata = manifest.get("kdp_listing_metadata") or {}
    listing_validation = validate_kdp_listing_metadata(listing_metadata, paperback=True)
    if listing_validation["blockers"]:
        blockers.extend("Fiche KDP : " + item for item in listing_validation["blockers"])
    else:
        normalized_listing = listing_validation["normalized_draft"]
        for field in ("title", "author", "language", "description"):
            _missing(
                normalized_listing.get(field) == metadata.get(field),
                f"La fiche KDP et le dossier éditorial divergent pour {field}.",
                blockers,
            )
        _missing(
            normalized_listing.get("rights_holder") == (manifest.get("rights") or {}).get("rights_holder")
            and normalized_listing.get("rights_evidence_ref") == (manifest.get("rights") or {}).get("evidence_ref"),
            "La fiche KDP et la preuve des droits divergent.",
            blockers,
        )
        pricing_record = manifest.get("pricing") or {}
        _missing(
            normalized_listing.get("marketplace") == pricing_record.get("marketplace")
            and normalized_listing.get("currency") == pricing_record.get("currency")
            and normalized_listing.get("list_price") == pricing_record.get("list_price"),
            "La fiche KDP et le calcul de prix divergent.",
            blockers,
        )
    _missing(
        isinstance(metadata.get("title"), str) and bool(metadata.get("title", "").strip()),
        "Titre définitif manquant.", blockers,
    )
    _missing(
        isinstance(metadata.get("author"), str) and bool(metadata.get("author", "").strip()),
        "Nom d'auteur confirmé manquant.", blockers,
    )
    _missing(metadata.get("language") == "fr", "Langue éditoriale non confirmée (fr attendu).", blockers)
    _missing(
        isinstance(metadata.get("description"), str) and 50 <= len(metadata.get("description", "")) <= 4000,
        "Description commerciale définitive manquante ou hors limites.", blockers,
    )
    _missing(
        isinstance(metadata.get("keywords"), list) and 1 <= len(metadata["keywords"]) <= 7
        and all(isinstance(item, str) and item.strip() for item in metadata["keywords"]),
        "Entre 1 et 7 mots-clés valides sont requis.", blockers,
    )

    editorial = manifest.get("editorial_approval") or {}
    _missing(editorial.get("approved") is True, "Validation éditoriale humaine absente.", blockers)
    _missing(bool(editorial.get("reviewer_id")) and bool(editorial.get("approved_at")),
             "Identité/date de validation éditoriale manquante.", blockers)

    rights = manifest.get("rights") or {}
    _missing(rights.get("commercial_use_confirmed") is True,
             "Droits d'exploitation commerciale non confirmés.", blockers)
    _missing(bool(rights.get("rights_holder")) and bool(rights.get("evidence_ref")),
             "Titulaire des droits ou preuve écrite manquant.", blockers)

    manuscript_sha256 = manifest.get("manuscript_sha256")
    safety_review = manifest.get("content_safety_review") or {}
    _missing(
        isinstance(manuscript_sha256, str) and bool(_SHA256.fullmatch(manuscript_sha256))
        and safety_review.get("approved") is True
        and bool(safety_review.get("reviewer_id"))
        and bool(safety_review.get("reviewed_at"))
        and bool(safety_review.get("evidence_ref"))
        and safety_review.get("manuscript_sha256") == manuscript_sha256,
        "Revue humaine de sécurité jeunesse absente ou liée à une autre version du manuscrit.",
        blockers,
    )

    try:
        page_count = int(manifest.get("page_count", 0))
    except (TypeError, ValueError):
        page_count = 0
    _missing(page_count >= 24 and page_count % 2 == 0,
             "Pagination imprimée paire d'au moins 24 pages requise.", blockers)
    print_spec = manifest.get("print_spec") or {}
    trim_width = print_spec.get("trim_width_in")
    trim_height = print_spec.get("trim_height_in")
    bleed = print_spec.get("bleed") is True
    assets = manifest.get("illustrations")
    asset_pages = []
    if isinstance(assets, list):
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            asset_pages.append(asset.get("page_number"))
            _missing(asset.get("review_status") == "approved",
                     f"Illustration page {asset.get('page_number')} non approuvée.", blockers)
            _missing(bool(_SHA256.fullmatch(str(asset.get("sha256", "")))),
                     f"Empreinte image manquante page {asset.get('page_number')}.", blockers)
            _missing(
                isinstance(asset.get("dpi"), (int, float)) and asset["dpi"] >= 300,
                f"Résolution pixel inférieure à 300 DPI ou inconnue page {asset.get('page_number')}.", blockers,
            )
            if isinstance(trim_width, (int, float)) and isinstance(trim_height, (int, float)):
                resolution_review = asset.get("resolution_review") or {
                    "approved": bool(asset.get("resolution_reviewed_by") and asset.get("resolution_reviewed_at")
                                     and asset.get("resolution_review_output_sha256") == asset.get("sha256")),
                    "reviewer_id": asset.get("resolution_reviewed_by"),
                    "approved_at": asset.get("resolution_reviewed_at"),
                    "output_sha256": asset.get("resolution_review_output_sha256"),
                }
                try:
                    resolution = audit_image_resolution(
                        source_width_px=asset.get("source_width_px", asset.get("width_px", 0)),
                        source_height_px=asset.get("source_height_px", asset.get("height_px", 0)),
                        final_width_px=asset.get("width_px", 0),
                        final_height_px=asset.get("height_px", 0),
                        trim_width_in=trim_width, trim_height_in=trim_height, bleed=bleed,
                        output_sha256=asset.get("sha256", ""),
                        upscaling_method=asset.get("upscaling_method", "native"),
                        resolution_review=resolution_review,
                    )
                    _missing(resolution["print_ready"],
                             f"Résolution source ou revue de super-résolution insuffisante page {asset.get('page_number')}.",
                             blockers)
                except (PrintResolutionError, TypeError, ValueError):
                    blockers.append(f"Provenance de résolution invalide page {asset.get('page_number')}.")
    else:
        assets = []
    _missing(
        sorted(asset_pages) == list(range(1, page_count + 1)),
        "Le registre doit contenir exactement une illustration approuvée pour chaque page.",
        blockers,
    )

    root = Path(private_root).resolve()
    pdfs = manifest.get("pdfs") or {}
    for key, expected_pages in (("interior", page_count), ("cover", 1)):
        record = pdfs.get(key) if isinstance(pdfs, dict) else None
        _missing(isinstance(record, dict), f"PDF {key} manquant.", blockers)
        if not isinstance(record, dict):
            continue
        relative_path = record.get("path", "")
        if not isinstance(relative_path, str) or not relative_path or Path(relative_path).is_absolute() or ".." in Path(relative_path).parts:
            blockers.append(f"Chemin du PDF {key} invalide.")
            continue
        path = (root / relative_path).resolve()
        if root not in path.parents or not path.is_file():
            blockers.append(f"Fichier PDF {key} absent du stockage privé.")
            continue
        data = path.read_bytes()
        _missing(data.startswith(b"%PDF-"), f"Fichier {key} n'est pas un PDF valide.", blockers)
        actual_page_count = len(re.findall(rb"/Type\s*/Page\b", data))
        _missing(actual_page_count == expected_pages,
                 f"Pagination réelle du PDF {key} incorrecte.", blockers)
        _missing(b"/Encrypt" not in data, f"PDF {key} chiffré ou verrouillé.", blockers)
        digest = hashlib.sha256(data).hexdigest()
        _missing(record.get("sha256") == digest, f"SHA-256 du PDF {key} incorrect.", blockers)
        _missing(record.get("page_count") == expected_pages,
                 f"Nombre de pages PDF {key} incorrect.", blockers)
        _missing(record.get("preflight") == "passed",
                 f"Préflight final du PDF {key} non validé.", blockers)

    _missing(isinstance(trim_width, (int, float)) and isinstance(trim_height, (int, float)),
             "Dimensions exactes du format imprimé manquantes.", blockers)
    _missing(bool(print_spec.get("trim_size")) and bool(print_spec.get("paper_type"))
             and print_spec.get("color_mode") in {"premium_color", "standard_color"}
             and isinstance(print_spec.get("cover_template_sha256"), str)
             and bool(_SHA256.fullmatch(print_spec.get("cover_template_sha256", ""))),
             "Format, papier, mode couleur ou gabarit officiel KDP manquant.", blockers)

    account = manifest.get("kdp_account") or {}
    _missing(account.get("eligibility_verified") is True and bool(account.get("verified_at"))
             and bool(account.get("evidence_ref")),
             "Éligibilité du compte KDP, versement et fiscalité non vérifiés.", blockers)

    pricing = manifest.get("pricing") or {}
    _missing(
        pricing.get("verified") is True
        and isinstance(pricing.get("marketplace"), str)
        and isinstance(pricing.get("currency"), str)
        and isinstance(pricing.get("list_price"), (int, float))
        and pricing.get("list_price", 0) > 0
        and isinstance(pricing.get("estimated_print_cost"), (int, float))
        and pricing.get("estimated_print_cost", -1) >= 0
        and isinstance(pricing.get("estimated_royalty"), (int, float))
        and pricing.get("verified_at"),
        "Prix, coût d'impression et redevance non vérifiés avec données datées.", blockers,
    )

    authorization = manifest.get("publication_authorization") or {}
    _missing(authorization.get("authorized") is True
             and bool(authorization.get("authorization_ref"))
             and bool(authorization.get("authorized_at")),
             "Autorisation explicite de publication du propriétaire absente.", blockers)

    ebook_required = manifest.get("ebook_required") is True
    ebook_summary = {"required": ebook_required, "status": "not_requested"}
    if ebook_required:
        ebook = manifest.get("ebook") or {}
        relative_path = ebook.get("path", "")
        if (not isinstance(relative_path, str) or not relative_path
                or Path(relative_path).is_absolute() or ".." in Path(relative_path).parts):
            blockers.append("Chemin du fichier EPUB invalide.")
        else:
            ebook_path = (root / relative_path).resolve()
            if root not in ebook_path.parents or not ebook_path.is_file():
                blockers.append("Fichier EPUB absent du stockage privé.")
            else:
                ebook_digest = hashlib.sha256(ebook_path.read_bytes()).hexdigest()
                _missing(ebook.get("sha256") == ebook_digest, "SHA-256 du fichier EPUB incorrect.", blockers)
                try:
                    ebook_preflight = validate_epub_structure(ebook_path, page_count)
                    ebook_summary.update(ebook_preflight)
                except PapiKidsEPUBPackageError:
                    blockers.append("Structure EPUB invalide ou incomplète.")
                _missing(ebook.get("page_count") == page_count,
                         "Pagination EPUB incorrecte.", blockers)
                _missing(ebook.get("preflight") == "passed",
                         "Préflight structurel EPUB non validé.", blockers)
                _missing(ebook.get("format") == "EPUB 3 fixed-layout",
                         "Format EPUB fixed-layout non confirmé.", blockers)
                preview = manifest.get("kindle_previewer_review") or {}
                _missing(
                    preview.get("passed") is True
                    and bool(preview.get("reviewer_id"))
                    and bool(preview.get("reviewed_at"))
                    and bool(preview.get("evidence_ref"))
                    and preview.get("epub_sha256") == ebook_digest,
                    "Validation Kindle Previewer humaine absente ou liée à une autre version EPUB.",
                    blockers,
                )
                ebook_summary.update({
                    "status": "approved" if preview.get("passed") is True else "pending_kindle_previewer",
                    "sha256": ebook_digest,
                })

    _missing(manifest.get("spend_limit_minor") == 0,
             "Le plafond de dépense doit rester strictement à zéro.", blockers)

    ready = not blockers
    return {
        "book_id": book_id,
        "status": "ready_for_manual_submission" if ready else "blocked",
        "publish_ready": ready,
        "publication_execution_enabled": False,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "human_authorization_present": authorization.get("authorized") is True,
        "spend_limit_minor": manifest.get("spend_limit_minor"),
        "publication_performed": False,
        "ebook": ebook_summary,
        "content_safety_review": {
            "approved": safety_review.get("approved") is True,
            "manuscript_sha256": safety_review.get("manuscript_sha256"),
            "reviewer_id": safety_review.get("reviewer_id"),
        },
        "listing_metadata": {
            "status": listing_validation["status"],
            "blocker_count": listing_validation["blocker_count"],
        },
    }
