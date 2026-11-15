"""Explicit owner-triggered KDP package build from a private server-side profile."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
import hashlib
import shutil
from typing import Any

from .papi_kids_kdp_package import (
    PapiKidsKDPPrintPackageError,
    build_kdp_print_package,
)


class PapiKidsKDPBuildServiceError(ValueError):
    """KDP build is disabled, unconfigured or invalid."""


_FORBIDDEN_KEYS = {
    "token", "secret", "password", "api_key", "authorization",
    "storage_root", "output_path", "upload_id",
}


def _reject_secrets(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = str(key).casefold()
            if (normalized_key in _FORBIDDEN_KEYS
                    or any(fragment in normalized_key for fragment in ("token", "secret", "password", "api_key", "authorization"))):
                raise PapiKidsKDPBuildServiceError("Le profil de fabrication contient un champ interdit.")
            _reject_secrets(child)
    elif isinstance(value, list):
        for child in value:
            _reject_secrets(child)


def build_kdp_package_from_private_profile(
    storage_root: str | Path,
    upload_id: str,
) -> dict[str, Any]:
    """Read a private 0600 build profile and create the approved multi-format package."""
    if not isinstance(upload_id, str) or not re.fullmatch(r"PKP-UP-[0-9a-f]{32}", upload_id):
        raise PapiKidsKDPBuildServiceError("Référence de dépôt invalide.")
    root = Path(storage_root).resolve()
    book_dir = (root / upload_id).resolve()
    if book_dir.parent != root or not book_dir.is_dir():
        raise PapiKidsKDPBuildServiceError("Dossier privé du manuscrit introuvable.")
    config_path = book_dir / "kdp-build-config.json"
    if config_path.is_symlink() or not config_path.is_file():
        raise PapiKidsKDPBuildServiceError("Profil de fabrication KDP absent ou symbolique.")
    if config_path.stat().st_size > 256 * 1024:
        raise PapiKidsKDPBuildServiceError("Profil de fabrication trop volumineux.")
    if stat.S_IMODE(config_path.stat().st_mode) & 0o077:
        raise PapiKidsKDPBuildServiceError("Le profil doit être privé (mode 0600).")
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PapiKidsKDPBuildServiceError("Profil JSON illisible.") from exc
    if not isinstance(config, dict):
        raise PapiKidsKDPBuildServiceError("Profil de fabrication invalide.")
    allowed = {"package_version", "interior_args", "cover_args", "ebook_args", "ebook_required"}
    if set(config) - allowed:
        raise PapiKidsKDPBuildServiceError("Le profil contient des propriétés non autorisées.")
    _reject_secrets(config)
    interior_args = config.get("interior_args")
    cover_args = config.get("cover_args")
    ebook_args = config.get("ebook_args")
    ebook_required = config.get("ebook_required", False)
    if not isinstance(interior_args, dict) or not isinstance(cover_args, dict):
        raise PapiKidsKDPBuildServiceError("Paramètres intérieurs ou couverture manquants.")
    if ebook_args is not None and not isinstance(ebook_args, dict):
        raise PapiKidsKDPBuildServiceError("Paramètres ebook invalides.")
    try:
        result = build_kdp_print_package(
            storage_root=root,
            upload_id=upload_id,
            interior_args=interior_args,
            cover_args=cover_args,
            ebook_args=ebook_args,
            ebook_required=ebook_required,
            package_version=config.get("package_version", 1),
        )
    except PapiKidsKDPPrintPackageError as exc:
        raise PapiKidsKDPBuildServiceError(str(exc)) from exc
    return {
        "upload_id": upload_id,
        "package_dir": result["package_dir"],
        "manifest_path": result["manifest_path"],
        "manifest": result["manifest"],
        "status": result["status"],
        "kdp_upload_ready": False,
        "publication_performed": False,
        "spend_limit_minor": 0,
    }


def build_private_kdp_package_handler(
    storage_root: str | Path,
    connection_factory,
):
    """Create a callback that builds locally and persists the manifest transactionally."""
    from .papi_kids_postgres_queue import record_kdp_package_build

    def build(upload_id: str) -> dict[str, Any]:
        result = build_kdp_package_from_private_profile(storage_root, upload_id)
        canonical = json.dumps(result["manifest"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        manifest_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        try:
            persisted = record_kdp_package_build(
                connection_factory, upload_id=upload_id,
                package_manifest=result["manifest"],
                package_manifest_sha256=manifest_sha256,
                build_status=result["status"],
            )
        except Exception:
            package_dir = Path(result["package_dir"]).resolve()
            book_dir = (Path(storage_root).resolve() / upload_id).resolve()
            if package_dir.parent == book_dir and package_dir.name.startswith("kdp-print-package-v"):
                shutil.rmtree(package_dir, ignore_errors=True)
            raise
        result["package_manifest_sha256"] = manifest_sha256
        result["persisted_package_build"] = persisted
        return result
    return build


def build_private_kdp_package_downloader(
    storage_root: str | Path,
    connection_factory,
):
    """Build an authenticated download callback for the latest package artifacts."""
    from .papi_kids_postgres_queue import build_postgres_status_reader

    status_reader = build_postgres_status_reader(connection_factory)
    root = Path(storage_root).resolve()

    def download(upload_id: str, artifact: str) -> dict[str, Any]:
        if artifact not in {"interior", "cover", "ebook"}:
            raise PapiKidsKDPBuildServiceError("Type de fichier KDP invalide.")
        status = status_reader(upload_id)
        package = status.get("kdp_package_build") or {}
        if artifact in {"interior", "cover"}:
            record = (package.get("pdfs") or {}).get(artifact)
        else:
            record = package.get("ebook")
        if not isinstance(record, dict):
            raise PapiKidsKDPBuildServiceError("Fichier absent du dernier package.")
        relative = record.get("path")
        if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise PapiKidsKDPBuildServiceError("Chemin de package invalide.")
        path = (root / relative).resolve()
        if root not in path.parents or path.is_symlink() or not path.is_file():
            raise PapiKidsKDPBuildServiceError("Fichier privé introuvable.")
        if path.stat().st_size > 650 * 1024 * 1024:
            raise PapiKidsKDPBuildServiceError("Fichier trop volumineux pour le téléchargement web.")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != record.get("sha256"):
            raise PapiKidsKDPBuildServiceError("Empreinte du fichier incorrecte.")
        if artifact == "ebook":
            return {"data": data, "content_type": "application/epub+zip", "filename": "book.epub"}
        return {"data": data, "content_type": "application/pdf", "filename": f"{artifact}.pdf"}
    return download
