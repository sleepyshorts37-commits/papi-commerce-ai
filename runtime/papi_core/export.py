"""Export local complet des épreuves PAPI KIDS depuis un manuscrit validé."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from .epub import build_epub, inspect_epub
from .manuscript import render_manuscript_markdown, validate_manuscript
from .print_pdf import PrintLayout, build_print_interior_pdf


class BookExportError(RuntimeError):
    """Erreur d'export ou de persistance des fichiers."""


def _slug(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return (value or "papi-kids-book")[:70]


def _write_new(path: Path, content: bytes) -> None:
    try:
        with path.open("xb") as stream:
            stream.write(content)
            stream.flush()
    except FileExistsError as exc:
        raise BookExportError(f"Le fichier existe déjà : {path.name}. Aucun écrasement effectué.") from exc
    except OSError as exc:
        raise BookExportError(f"Impossible d'écrire le fichier : {path.name}.") from exc


def export_book_files(
    manuscript: dict[str, Any],
    output_dir: str | Path,
    *,
    layout: PrintLayout | None = None,
) -> dict[str, Any]:
    """Produit Markdown, EPUB 3, PDF de lecture et manifeste, sans publication externe."""
    report = validate_manuscript(manuscript)
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    if not directory.is_dir():
        raise BookExportError("Le chemin de sortie doit être un dossier.")
    stem = _slug(report.title)
    outputs = {
        f"{stem}.md": render_manuscript_markdown(manuscript).encode("utf-8"),
        f"{stem}.epub": build_epub(manuscript),
        f"{stem}-interior-proof.pdf": build_print_interior_pdf(manuscript, layout),
    }
    manifest = {
        "title": report.title,
        "language": report.language,
        "age_range": report.age_range,
        "word_count": report.word_count,
        "content_sha256": report.content_sha256,
        "files": [],
        "illustrations_included": False,
        "cover_included": False,
        "kdp_preflight": "required",
        "publication_status": "not_published",
        "owner_approval_required": True,
        "warnings": list(report.warnings),
    }
    for filename, content in outputs.items():
        _write_new(directory / filename, content)
        manifest["files"].append({
            "name": filename,
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        })
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _write_new(directory / f"{stem}-manifest.json", manifest_bytes)
    manifest["files"].append({
        "name": f"{stem}-manifest.json",
        "size_bytes": len(manifest_bytes),
        "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    })
    manifest["epub_inspection"] = inspect_epub(outputs[f"{stem}.epub"])
    return manifest
