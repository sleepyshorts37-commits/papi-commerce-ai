"""Private PAPI KIDS illustration asset storage with format and dimension checks."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Callable

_UPLOAD_ID = re.compile(r"^PKP-UP-[0-9a-f]{32}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MAX_BYTES = 20 * 1024 * 1024


class IllustrationAssetError(ValueError):
    """Invalid illustration payload or private asset storage failure."""


def _png_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def _jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    index = 2
    while index + 4 <= len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        while index < len(data) and data[index] == 0xFF:
            index += 1
        if index >= len(data):
            break
        marker = data[index]
        index += 1
        if marker in {0xD8, 0xD9, 0x01, *range(0xD0, 0xD8)}:
            continue
        if index + 2 > len(data):
            break
        segment_length = int.from_bytes(data[index:index + 2], "big")
        if segment_length < 2 or index + segment_length > len(data):
            break
        if marker in sof and segment_length >= 7:
            height = int.from_bytes(data[index + 3:index + 5], "big")
            width = int.from_bytes(data[index + 5:index + 7], "big")
            return width, height
        index += segment_length
    return None


def _webp_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 30 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    kind = data[12:16]
    if kind == b"VP8X" and len(data) >= 30:
        width = 1 + int.from_bytes(data[24:27], "little")
        height = 1 + int.from_bytes(data[27:30], "little")
        return width, height
    if kind == b"VP8 " and len(data) >= 30 and data[23:26] == b"\x9d\x01\x2a":
        width = int.from_bytes(data[26:28], "little") & 0x3FFF
        height = int.from_bytes(data[28:30], "little") & 0x3FFF
        return width, height
    if kind == b"VP8L" and len(data) >= 25 and data[20] == 0x2F:
        b1, b2, b3, b4 = data[21:25]
        width = 1 + (((b2 & 0x3F) << 8) | b1)
        height = 1 + (((b4 & 0x0F) << 10) | (b3 << 2) | ((b2 & 0xC0) >> 6))
        return width, height
    return None


def inspect_image(data: bytes, media_type: str) -> tuple[int, int]:
    if not isinstance(data, bytes) or not data or len(data) > _MAX_BYTES:
        raise IllustrationAssetError("Image vide ou supérieure à 20 Mio.")
    parsers = {
        "image/png": _png_dimensions,
        "image/jpeg": _jpeg_dimensions,
        "image/webp": _webp_dimensions,
    }
    parser = parsers.get(media_type)
    if parser is None:
        raise IllustrationAssetError("Format image non accepté.")
    dimensions = parser(data)
    if dimensions is None:
        raise IllustrationAssetError("Signature ou en-tête image invalide.")
    width, height = dimensions
    if not (1 <= width <= 12000 and 1 <= height <= 12000):
        raise IllustrationAssetError("Dimensions image hors limites.")
    return width, height


def _atomic_write(path: Path, data: bytes) -> None:
    fd, temporary_name = tempfile.mkstemp(prefix=".asset-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, path)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def store_illustration_asset(
    storage_root: str | Path,
    *,
    upload_id: str,
    page_number: int,
    version: int,
    image_bytes: bytes,
    media_type: str,
    source_provider: str | None = None,
    model_id: str | None = None,
    prompt_sha256: str | None = None,
    generation_ref: str | None = None,
    source_width_px: int | None = None,
    source_height_px: int | None = None,
    upscaling_method: str = "native",
    resolution_review: dict[str, Any] | None = None,
    asset_registrar: Callable[[dict[str, Any]], Any] | None = None,
) -> dict[str, Any]:
    """Persist one private image version; final visual/editorial approval stays human."""
    if not isinstance(upload_id, str) or not _UPLOAD_ID.fullmatch(upload_id):
        raise IllustrationAssetError("Référence de dépôt invalide.")
    if not isinstance(page_number, int) or isinstance(page_number, bool) or not 1 <= page_number <= 200:
        raise IllustrationAssetError("Numéro de page invalide.")
    if not isinstance(version, int) or isinstance(version, bool) or not 1 <= version <= 1000:
        raise IllustrationAssetError("Version d'image invalide.")
    if prompt_sha256 is not None and not _SHA256.fullmatch(prompt_sha256):
        raise IllustrationAssetError("Empreinte du prompt invalide.")
    width, height = inspect_image(image_bytes, media_type)
    digest = hashlib.sha256(image_bytes).hexdigest()
    source_width_px = width if source_width_px is None else source_width_px
    source_height_px = height if source_height_px is None else source_height_px
    if (not isinstance(source_width_px, int) or isinstance(source_width_px, bool)
            or not 1 <= source_width_px <= 12000
            or not isinstance(source_height_px, int) or isinstance(source_height_px, bool)
            or not 1 <= source_height_px <= 12000):
        raise IllustrationAssetError("Dimensions source invalides.")
    if upscaling_method not in {"native", "ai_super_resolution", "manual_retouch", "lanczos_only"}:
        raise IllustrationAssetError("Méthode d'agrandissement invalide.")
    if resolution_review is not None:
        if not isinstance(resolution_review, dict):
            raise IllustrationAssetError("Preuve de revue de résolution invalide.")
        if resolution_review.get("approved") is True and (
            not resolution_review.get("reviewer_id")
            or not resolution_review.get("approved_at")
            or resolution_review.get("output_sha256") != digest
        ):
            raise IllustrationAssetError("La revue de résolution doit être liée au SHA-256 final.")
    asset_id = "PKP-ASSET-" + digest[:24]
    extension = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}[media_type]
    root = Path(storage_root).resolve()
    book_dir = (root / upload_id).resolve()
    if book_dir.parent != root or not book_dir.is_dir():
        raise IllustrationAssetError("Dossier de manuscrit privé introuvable.")
    asset_dir = book_dir / "illustrations"
    asset_dir.mkdir(mode=0o700, exist_ok=True)
    os.chmod(asset_dir, 0o700)
    filename = f"page-{page_number:02d}-v{version:03d}{extension}"
    target = asset_dir / filename
    metadata_path = asset_dir / f"page-{page_number:02d}-v{version:03d}.json"
    storage_key = f"{upload_id}/illustrations/{filename}"
    metadata = {
        "asset_id": asset_id,
        "upload_id": upload_id,
        "page_number": page_number,
        "version": version,
        "sha256": digest,
        "storage_key": storage_key,
        "media_type": media_type,
        "width_px": width,
        "height_px": height,
        "source_width_px": source_width_px,
        "source_height_px": source_height_px,
        "upscaling_method": upscaling_method,
        "resolution_review": resolution_review or {},
        "source_provider": source_provider,
        "model_id": model_id,
        "prompt_sha256": prompt_sha256,
        "generation_ref": generation_ref,
        "review_status": "pending_review",
        "human_approval_required": True,
        "persistence_status": "local_only",
    }
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise IllustrationAssetError("Cette page/version existe déjà avec une autre image.")
    else:
        _atomic_write(target, image_bytes)
    if metadata_path.exists():
        existing = json.loads(metadata_path.read_text(encoding="utf-8"))
        if existing.get("sha256") != digest:
            raise IllustrationAssetError("Métadonnées de version incohérentes.")
        if (existing.get("source_width_px", existing.get("width_px")) != source_width_px
                or existing.get("source_height_px", existing.get("height_px")) != source_height_px
                or existing.get("upscaling_method", "native") != upscaling_method):
            raise IllustrationAssetError("Provenance source différente pour cette version d'image.")
        metadata = existing
    if asset_registrar is not None:
        try:
            asset_registrar(metadata)
            metadata["persistence_status"] = "registered"
        except Exception:
            metadata["persistence_status"] = "pending_retry"
            _atomic_write(metadata_path, json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"))
            return metadata
    _atomic_write(metadata_path, json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"))
    return metadata
