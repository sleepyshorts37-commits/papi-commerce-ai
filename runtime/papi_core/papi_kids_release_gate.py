"""Strict final release gate for Amazon KDP; never uploads or publishes."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
from typing import Any

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

    try:
        page_count = int(manifest.get("page_count", 0))
    except (TypeError, ValueError):
        page_count = 0
    _missing(page_count >= 24 and page_count % 2 == 0,
             "Pagination imprimée paire d'au moins 24 pages requise.", blockers)
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
                f"Résolution inférieure à 300 DPI ou inconnue page {asset.get('page_number')}.", blockers,
            )
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
        actual_page_count = len(re.findall(rb"/Type\\s*/Page\\b", data))
        _missing(actual_page_count == expected_pages,
                 f"Pagination réelle du PDF {key} incorrecte.", blockers)
        _missing(b"/Encrypt" not in data, f"PDF {key} chiffré ou verrouillé.", blockers)
        digest = hashlib.sha256(data).hexdigest()
        _missing(record.get("sha256") == digest, f"SHA-256 du PDF {key} incorrect.", blockers)
        _missing(record.get("page_count") == expected_pages,
                 f"Nombre de pages PDF {key} incorrect.", blockers)
        _missing(record.get("preflight") == "passed",
                 f"Préflight final du PDF {key} non validé.", blockers)

    print_spec = manifest.get("print_spec") or {}
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
    }
