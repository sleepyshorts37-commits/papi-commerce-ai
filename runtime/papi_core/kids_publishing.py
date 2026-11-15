"""Read-only catalog and production gates for PAPI KIDS PUBLISHING.

This module prepares and audits book projects locally. It never creates files,
contacts platforms, submits books, publishes listings, or changes agent states.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CATALOG_FILE = ROOT / "data" / "divisions" / "papi-kids-catalog.json"
MAX_CATALOG_BYTES = 2 * 1024 * 1024
MAX_ASSET_BYTES = 100 * 1024 * 1024
BOOK_ID_RE = re.compile(r"^PKP-[A-Z0-9]{4,20}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

PRODUCT_TYPES = {"coloring_book", "illustrated_story", "educational_book", "activity_book", "ebook"}
FORMATS = {"paperback", "ebook", "both"}
WORKFLOW_STAGES = {
    "idea", "research", "rights_review", "concept", "draft", "illustration",
    "layout", "quality_review", "kdp_preparation", "ready_for_human_review",
    "blocked", "withdrawn",
}
REVIEW_STATUSES = {"pending", "passed", "failed", "not_checked"}
ASSET_KINDS = {"manuscript", "interior_pdf", "cover_pdf", "metadata", "quality_report"}
REQUIRED_ASSETS = {
    "paperback": {"manuscript", "interior_pdf", "cover_pdf", "metadata", "quality_report"},
    "ebook": {"manuscript", "metadata", "quality_report"},
    "both": {"manuscript", "interior_pdf", "cover_pdf", "metadata", "quality_report"},
}


class KidsPublishingError(ValueError):
    """Erreur de validation du catalogue éditorial."""


def _reject_constant(value: str) -> None:
    raise KidsPublishingError(f"Constante JSON non standard interdite: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise KidsPublishingError(f"Clé JSON dupliquée: {key}")
        result[key] = value
    return result


def _strict_json_bytes(raw: bytes) -> Any:
    if len(raw) > MAX_CATALOG_BYTES:
        raise KidsPublishingError("Catalogue trop volumineux.")
    try:
        text = raw.decode("utf-8", errors="strict")
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise KidsPublishingError("Catalogue JSON/UTF-8 invalide.") from exc


def load_catalog(path: Path = CATALOG_FILE) -> dict[str, Any]:
    try:
        if path.is_symlink() or path.stat().st_size > MAX_CATALOG_BYTES:
            raise KidsPublishingError("Catalogue symbolique ou trop volumineux.")
        raw = path.read_bytes()
    except KidsPublishingError:
        raise
    except OSError as exc:
        raise KidsPublishingError("Catalogue introuvable ou illisible.") from exc
    data = _strict_json_bytes(raw)
    if not isinstance(data, dict):
        raise KidsPublishingError("Le catalogue doit être un objet JSON.")
    return data


def _validate_book(book: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(book, dict):
        return ["Le livre doit être un objet."]
    required = {
        "book_id", "title", "language", "product_type", "format",
        "target_age_min", "target_age_max", "workflow_stage",
        "original_work", "rights_status", "quality_status",
        "kdp_compliance_status", "human_approval", "assets",
    }
    missing = sorted(required - set(book))
    if missing:
        errors.append("Champs obligatoires absents: " + ", ".join(missing))
        return errors

    book_id = book["book_id"]
    if not isinstance(book_id, str) or not BOOK_ID_RE.fullmatch(book_id):
        errors.append("book_id doit respecter PKP- suivi de 4 à 20 caractères A-Z/0-9.")
    title = book["title"]
    if not isinstance(title, str) or not title.strip() or len(title) > 200:
        errors.append("title doit contenir entre 1 et 200 caractères.")
    language = book["language"]
    if not isinstance(language, str) or not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})?", language):
        errors.append("language doit être un code de langue simple, par exemple fr ou en.")
    if not isinstance(book["product_type"], str) or book["product_type"] not in PRODUCT_TYPES:
        errors.append("product_type invalide.")
    if not isinstance(book["format"], str) or book["format"] not in FORMATS:
        errors.append("format invalide.")
    for field in ("target_age_min", "target_age_max"):
        if isinstance(book[field], bool) or not isinstance(book[field], int) or not 0 <= book[field] <= 18:
            errors.append(f"{field} doit être un entier entre 0 et 18.")
    if all(isinstance(book[field], int) and not isinstance(book[field], bool) for field in ("target_age_min", "target_age_max")):
        if book["target_age_min"] > book["target_age_max"]:
            errors.append("La tranche d'âge est inversée.")
    if not isinstance(book["workflow_stage"], str) or book["workflow_stage"] not in WORKFLOW_STAGES:
        errors.append("workflow_stage invalide.")
    if not isinstance(book["original_work"], bool):
        errors.append("original_work doit être booléen.")
    for field in ("rights_status", "quality_status", "kdp_compliance_status"):
        if not isinstance(book[field], str) or book[field] not in REVIEW_STATUSES:
            errors.append(f"{field} invalide.")

    approval = book["human_approval"]
    if not isinstance(approval, dict) or set(approval) - {"status", "approved_by", "approved_at", "reference"}:
        errors.append("human_approval doit être un objet avec des champs autorisés.")
    elif not isinstance(approval.get("status", "pending"), str) or approval.get("status", "pending") not in {"pending", "approved", "rejected"}:
        errors.append("Statut human_approval invalide.")
    elif approval.get("status") == "approved":
        for field in ("approved_by", "approved_at", "reference"):
            if not isinstance(approval.get(field), str) or not approval[field].strip():
                errors.append(f"Une approbation doit inclure {field}.")

    assets = book["assets"]
    if not isinstance(assets, list):
        errors.append("assets doit être une liste.")
    else:
        seen: set[str] = set()
        for asset in assets:
            if not isinstance(asset, dict) or set(asset) != {"kind", "path", "sha256"}:
                errors.append("Chaque asset doit contenir exactement kind, path et sha256.")
                continue
            kind, path, digest = asset["kind"], asset["path"], asset["sha256"]
            if not isinstance(kind, str) or kind not in ASSET_KINDS:
                errors.append("Type d'asset inconnu.")
            elif kind in seen:
                errors.append(f"Asset dupliqué: {kind}.")
            if isinstance(kind, str) and kind in ASSET_KINDS:
                seen.add(kind)
            if not isinstance(path, str) or not path or Path(path).is_absolute() or "\\" in path:
                errors.append(f"Chemin d'asset invalide pour {kind}.")
            elif any(part in {"", ".", ".."} for part in path.split("/")):
                errors.append(f"Chemin d'asset non canonique pour {kind}.")
            if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
                errors.append(f"SHA-256 invalide pour {kind}.")
            if isinstance(path, str):
                suffix = Path(path).suffix.lower()
                allowed_suffixes = {
                    "manuscript": {".md", ".txt"},
                    "interior_pdf": {".pdf"},
                    "cover_pdf": {".pdf"},
                    "metadata": {".json"},
                    "quality_report": {".json"},
                }
                if isinstance(kind, str) and kind in allowed_suffixes and suffix not in allowed_suffixes[kind]:
                    errors.append(f"Extension de fichier invalide pour {kind}.")
    return errors


def validate_catalog(data: dict[str, Any]) -> list[str]:
    if set(data) != {"schema_version", "division_id", "books"}:
        return ["Le catalogue doit contenir exactement schema_version, division_id et books."]
    if data.get("schema_version") != 1 or data.get("division_id") != "papi_kids_publishing":
        return ["Version ou division du catalogue invalide."]
    books = data.get("books")
    if not isinstance(books, list):
        return ["books doit être une liste."]
    errors: list[str] = []
    seen: set[str] = set()
    for index, book in enumerate(books):
        for error in _validate_book(book):
            errors.append(f"Livre #{index + 1}: {error}")
        if isinstance(book, dict) and isinstance(book.get("book_id"), str):
            if book["book_id"] in seen:
                errors.append(f"Identifiant de livre dupliqué: {book['book_id']}.")
            seen.add(book["book_id"])
    return errors


def _asset_status(asset: dict[str, Any], root: Path) -> tuple[bool, str]:
    relative = Path(asset["path"])
    candidate = root / relative
    try:
        current = root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                return False, "symlink_refused"
        resolved_root = root.resolve(strict=True)
        resolved = candidate.resolve(strict=True)
        if resolved_root not in resolved.parents:
            return False, "path_escape_refused"
        if not resolved.is_file():
            return False, "not_a_regular_file"
        if resolved.stat().st_size > MAX_ASSET_BYTES:
            return False, "asset_too_large"
        digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
    except OSError:
        return False, "missing_or_unreadable"
    if digest != asset["sha256"]:
        return False, "sha256_mismatch"
    return True, "verified"


def inspect_book(book: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    """Return a deterministic readiness assessment; never writes or publishes."""
    errors = _validate_book(book)
    if errors:
        return {
            "book_id": book.get("book_id") if isinstance(book, dict) else None,
            "valid": False,
            "errors": errors,
            "ready_for_human_review": False,
            "external_submission_performed": False,
        }

    required_assets = REQUIRED_ASSETS[book["format"]]
    by_kind = {asset["kind"]: asset for asset in book["assets"]}
    asset_results: dict[str, str] = {}
    for kind in sorted(required_assets):
        if kind not in by_kind:
            asset_results[kind] = "missing_reference"
            continue
        valid, status = _asset_status(by_kind[kind], root)
        asset_results[kind] = status if valid else status

    technical_blockers: list[str] = []
    if book["original_work"] is not True:
        technical_blockers.append("original_work_not_confirmed")
    if book["rights_status"] != "passed":
        technical_blockers.append("rights_review_not_passed")
    if book["quality_status"] != "passed":
        technical_blockers.append("independent_quality_gate_not_passed")
    if book["kdp_compliance_status"] != "passed":
        technical_blockers.append("kdp_compliance_review_not_passed")
    for kind, status in asset_results.items():
        if status != "verified":
            technical_blockers.append(f"asset_{kind}_{status}")
    approval_status = book["human_approval"].get("status", "pending")
    blockers = list(technical_blockers)
    if approval_status != "approved":
        blockers.append("human_publication_approval_pending")

    return {
        "book_id": book["book_id"],
        "valid": True,
        "workflow_stage": book["workflow_stage"],
        "asset_checks": asset_results,
        "technical_blockers": technical_blockers,
        "blockers": blockers,
        "ready_for_human_review": not technical_blockers and approval_status == "pending",
        "approved_for_manual_submission": not blockers and approval_status == "approved",
        "human_approval_recorded": approval_status == "approved",
        "external_submission_performed": False,
        "external_publication_performed": False,
        "note": "Évaluation locale uniquement ; aucune soumission ou publication KDP n'est effectuée.",
    }


def build_catalog_report(path: Path = CATALOG_FILE) -> dict[str, Any]:
    data = load_catalog(path)
    errors = validate_catalog(data)
    if errors:
        raise KidsPublishingError("; ".join(errors))
    books = data["books"]
    stages = Counter(book["workflow_stage"] for book in books)
    assessments = [inspect_book(book, root=path.parent.parent.parent) for book in books]
    return {
        "division_id": data["division_id"],
        "total_books": len(books),
        "books_by_stage": dict(sorted(stages.items())),
        "ready_for_human_review": sum(item["ready_for_human_review"] for item in assessments),
        "approved_for_manual_submission": sum(item["approved_for_manual_submission"] for item in assessments),
        "blocked_or_incomplete": sum(not item["ready_for_human_review"] and not item["approved_for_manual_submission"] for item in assessments),
        "external_actions_performed": False,
    }


def check_book(book_id: str, path: Path = CATALOG_FILE) -> dict[str, Any]:
    data = load_catalog(path)
    errors = validate_catalog(data)
    if errors:
        raise KidsPublishingError("; ".join(errors))
    matches = [book for book in data["books"] if book["book_id"] == book_id]
    if len(matches) != 1:
        raise KidsPublishingError("Identifiant de livre absent ou ambigu.")
    return inspect_book(matches[0], root=path.parent.parent.parent)
