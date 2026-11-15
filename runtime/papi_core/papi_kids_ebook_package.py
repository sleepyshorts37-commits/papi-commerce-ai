"""Atomic fixed-layout EPUB package creation and structural preflight."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any
from xml.etree import ElementTree
from zipfile import ZIP_STORED, ZipFile

from .papi_kids_fixed_layout_epub import (
    KDPFixedLayoutEPUBError,
    build_kdp_fixed_layout_epub,
)

_UPLOAD_ID_PREFIX = "PKP-UP-"


class PapiKidsEPUBPackageError(ValueError):
    """EPUB package failed structural validation."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_epub_structure(path: str | Path, expected_pages: int) -> dict[str, Any]:
    """Validate ZIP integrity, EPUB mimetype order, XML documents and fixed-layout assets."""
    epub = Path(path)
    if not epub.is_file() or epub.stat().st_size > 650 * 1024 * 1024:
        raise PapiKidsEPUBPackageError("Fichier EPUB absent ou supérieur à 650 Mio.")
    try:
        with ZipFile(epub, "r") as archive:
            names = archive.namelist()
            if not names or names[0] != "mimetype":
                raise PapiKidsEPUBPackageError("Le fichier mimetype doit être le premier dans l'EPUB.")
            if len(names) != len(set(names)):
                raise PapiKidsEPUBPackageError("Entrées ZIP dupliquées.")
            if archive.getinfo("mimetype").compress_type != ZIP_STORED:
                raise PapiKidsEPUBPackageError("Le mimetype EPUB doit être stocké sans compression.")
            if archive.read("mimetype") != b"application/epub+zip":
                raise PapiKidsEPUBPackageError("Mimetype EPUB invalide.")
            if archive.testzip() is not None:
                raise PapiKidsEPUBPackageError("Archive ZIP corrompue.")
            required = {
                "META-INF/container.xml", "OEBPS/package.opf", "OEBPS/nav.xhtml",
                "OEBPS/styles/book.css", "OEBPS/pages/cover.xhtml",
            }
            if not required.issubset(set(names)):
                raise PapiKidsEPUBPackageError("Fichiers de structure EPUB manquants.")
            for name in names:
                if name.startswith("/") or ".." in Path(name).parts:
                    raise PapiKidsEPUBPackageError("Chemin interne EPUB invalide.")
                if name.endswith((".xml", ".xhtml", ".opf")):
                    ElementTree.fromstring(archive.read(name))
            page_docs = [
                name for name in names
                if name.startswith("OEBPS/pages/page-") and name.endswith(".xhtml")
            ]
            if len(page_docs) != expected_pages:
                raise PapiKidsEPUBPackageError("Nombre de pages XHTML incorrect.")
            opf = archive.read("OEBPS/package.opf")
            if b"pre-paginated" not in opf or b"rendition:layout" not in opf:
                raise PapiKidsEPUBPackageError("Le package OPF n'est pas déclaré fixed-layout.")
            for number in range(1, expected_pages + 1):
                page = archive.read(f"OEBPS/pages/page-{number:03d}.xhtml")
                if b"app-amzn-magnify" not in page:
                    raise PapiKidsEPUBPackageError(f"Pop-up Kindle absent page {number}.")
    except PapiKidsEPUBPackageError:
        raise
    except Exception as exc:
        raise PapiKidsEPUBPackageError("Archive EPUB illisible ou XML invalide.") from exc
    return {
        "zip_integrity": "passed",
        "xml_integrity": "passed",
        "page_count": expected_pages,
        "text_popups": True,
        "fixed_layout": True,
        "kindle_previewer_required": True,
        "kindle_previewer_passed": False,
    }


def build_kdp_ebook_package(
    *,
    storage_root: str | Path,
    upload_id: str,
    epub_args: dict[str, Any],
    package_version: int = 1,
) -> dict[str, Any]:
    """Build EPUB in private staging and atomically publish the validated package."""
    if not isinstance(upload_id, str) or not upload_id.startswith(_UPLOAD_ID_PREFIX) or len(upload_id) != 39:
        raise PapiKidsEPUBPackageError("Référence de dépôt invalide.")
    if not isinstance(package_version, int) or isinstance(package_version, bool) or not 1 <= package_version <= 999:
        raise PapiKidsEPUBPackageError("Version de package invalide.")
    if not isinstance(epub_args, dict) or {"storage_root", "output_path", "upload_id"}.intersection(epub_args):
        raise PapiKidsEPUBPackageError("Chemins et référence contrôlés par le service.")
    root = Path(storage_root).resolve()
    book_dir = (root / upload_id).resolve()
    if book_dir.parent != root or not book_dir.is_dir():
        raise PapiKidsEPUBPackageError("Dossier privé du manuscrit introuvable.")
    final_dir = book_dir / f"ebook-package-v{package_version:03d}"
    if final_dir.exists():
        raise PapiKidsEPUBPackageError("Cette version de package EPUB existe déjà.")
    page_count = len(epub_args.get("pages", [])) if isinstance(epub_args.get("pages"), list) else 0
    stage = Path(tempfile.mkdtemp(prefix=".ebook-package-", dir=book_dir))
    os.chmod(stage, 0o700)
    output = stage / "book.epub"
    try:
        generated = build_kdp_fixed_layout_epub(
            root, output, upload_id=upload_id, **epub_args
        )
        preflight = validate_epub_structure(output, page_count)
        manifest = {
            "schema_version": 1,
            "upload_id": upload_id,
            "package_version": package_version,
            "format": "EPUB 3 fixed-layout",
            "ebook": {
                "path": f"{upload_id}/ebook-package-v{package_version:03d}/book.epub",
                "sha256": _sha256(output),
                "page_count": page_count,
                "preflight": "pending_kindle_previewer",
                "structural_checks": preflight,
            },
            "human_approval_required": True,
            "kindle_previewer_required": True,
            "kdp_upload_ready": False,
            "upload_or_publication_performed": False,
            "spend_limit_minor": 0,
        }
        manifest_path = stage / "ebook-manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(manifest_path, 0o600)
        os.replace(stage, final_dir)
    except Exception as exc:
        shutil.rmtree(stage, ignore_errors=True)
        if isinstance(exc, (PapiKidsEPUBPackageError, KDPFixedLayoutEPUBError)):
            raise
        raise PapiKidsEPUBPackageError("La fabrication du package EPUB a échoué.") from exc
    return {
        "package_dir": str(final_dir),
        "manifest": manifest,
        "generated": generated,
        "status": "generated_pending_kindle_previewer",
        "kdp_upload_ready": False,
        "publication_performed": False,
        "spend_limit_minor": 0,
    }
