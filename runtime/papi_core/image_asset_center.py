"""Durable, local-first image asset library for PAPI IMAGE FACTORY.

This module stores generated image bytes and metadata atomically. It does not
call a provider, upload to cloud storage, or approve visual content.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")
_MODEL_ID = re.compile(r"^@[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$|^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_MAGIC = {
    "image/png": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": lambda b: b.startswith(b"\xff\xd8\xff"),
    "image/webp": lambda b: len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP",
}


class AssetCenterError(ValueError):
    """Invalid asset, metadata, review transition, or storage operation."""


def _safe(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _SAFE.fullmatch(value):
        raise AssetCenterError(f"{field} invalide.")
    return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".papi-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


class LocalImageAssetCenter:
    """Local durable asset store; use a private persistent volume in deployment."""

    def __init__(self, root: str | Path, *, max_asset_bytes: int = 25_000_000):
        if not isinstance(max_asset_bytes, int) or isinstance(max_asset_bytes, bool) or max_asset_bytes < 1:
            raise AssetCenterError("Limite de taille invalide.")
        self.root = Path(root).expanduser().resolve()
        self.max_asset_bytes = max_asset_bytes
        self.assets_dir = self.root / "assets"
        self.index_dir = self.root / "index"

    def _paths(self, book_id: str, page_id: str, idempotency_key: str) -> tuple[Path, Path]:
        book = _safe(book_id, "book_id")
        page = _safe(page_id, "page_id")
        key = _safe(idempotency_key, "idempotency_key")
        identity = hashlib.sha256(f"{book}\x1f{page}\x1f{key}".encode()).hexdigest()
        return self.assets_dir / book / f"{page}-{identity}.bin", self.index_dir / f"{identity}.json"

    @staticmethod
    def _detect_mime(data: bytes) -> str:
        for mime, check in _MAGIC.items():
            if check(data):
                return mime
        raise AssetCenterError("Format image non reconnu (PNG, JPEG ou WebP requis).")

    def put(
        self, *, book_id: str, page_id: str, page_number: int,
        idempotency_key: str, image_bytes: bytes, content_type: str | None = None,
        model: str, prompt_sha256: str | None = None,
    ) -> dict[str, Any]:
        """Persist one generated image; identical replay is idempotent."""
        book = _safe(book_id, "book_id")
        page = _safe(page_id, "page_id")
        if not isinstance(model, str) or not _MODEL_ID.fullmatch(model) or "//" in model or ".." in model:
            raise AssetCenterError("Identifiant de modèle invalide.")
        model_name = model
        if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
            raise AssetCenterError("Numéro de page invalide.")
        if not isinstance(image_bytes, bytes) or not image_bytes:
            raise AssetCenterError("Octets image absents.")
        if len(image_bytes) > self.max_asset_bytes:
            raise AssetCenterError("Image supérieure à la taille maximale autorisée.")
        detected = self._detect_mime(image_bytes)
        if content_type and content_type.split(";")[0].strip().lower() != detected:
            raise AssetCenterError("Le type MIME annoncé ne correspond pas au fichier.")
        if prompt_sha256 is not None and not re.fullmatch(r"[a-f0-9]{64}", prompt_sha256):
            raise AssetCenterError("Empreinte du prompt invalide.")
        asset_path, index_path = self._paths(book, page, idempotency_key)
        digest = hashlib.sha256(image_bytes).hexdigest()
        if index_path.exists():
            existing = json.loads(index_path.read_text(encoding="utf-8"))
            if existing.get("content_sha256") != digest:
                raise AssetCenterError("Clé d'idempotence déjà associée à un autre contenu.")
            return existing
        _atomic_write(asset_path, image_bytes)
        record = {
            "schema_version": 1, "book_id": book, "page_id": page,
            "page_number": page_number, "idempotency_key": idempotency_key,
            "model": model_name, "content_sha256": digest,
            "byte_length": len(image_bytes), "mime_type": detected,
            "relative_path": str(asset_path.relative_to(self.root)),
            "status": "pending_visual_review", "human_approved": False,
            "prompt_sha256": prompt_sha256, "created_at": _utc_now(),
        }
        try:
            _atomic_write(index_path, json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2).encode())
        except Exception:
            # Orphan bytes are harmless and can be reconciled; never delete a
            # possibly shared asset as a compensating action.
            raise
        return record

    def get(self, *, book_id: str, page_id: str, idempotency_key: str,
            page_number: int | None = None) -> dict[str, Any] | None:
        _, index_path = self._paths(book_id, page_id, idempotency_key)
        if not index_path.exists():
            return None
        return json.loads(index_path.read_text(encoding="utf-8"))

    def read_bytes(self, record: dict[str, Any]) -> bytes:
        relative = record.get("relative_path")
        if not isinstance(relative, str):
            raise AssetCenterError("Chemin d'asset absent.")
        path = (self.root / relative).resolve()
        if self.root not in path.parents:
            raise AssetCenterError("Chemin d'asset hors du stockage.")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != record.get("content_sha256"):
            raise AssetCenterError("Intégrité de l'asset compromise.")
        return data

    def list_assets(self, *, book_id: str, status: str | None = None) -> list[dict[str, Any]]:
        book = _safe(book_id, "book_id")
        records = []
        for path in sorted(self.index_dir.glob("*.json")) if self.index_dir.exists() else []:
            item = json.loads(path.read_text(encoding="utf-8"))
            if item.get("book_id") == book and (status is None or item.get("status") == status):
                records.append(item)
        return records

    def review(
        self, *, book_id: str, page_id: str, idempotency_key: str,
        decision: str, reviewer_id: str, evidence: str,
    ) -> dict[str, Any]:
        """Record a human review; no automated quality score can approve an image."""
        reviewer = _safe(reviewer_id, "reviewer_id")
        if decision not in {"approved", "rejected"}:
            raise AssetCenterError("Décision de revue invalide.")
        if not isinstance(evidence, str) or len(evidence.strip()) < 8 or len(evidence) > 2_000:
            raise AssetCenterError("Une justification de revue (8 à 2 000 caractères) est requise.")
        asset_path, index_path = self._paths(book_id, page_id, idempotency_key)
        if not index_path.exists():
            raise AssetCenterError("Asset introuvable.")
        record = json.loads(index_path.read_text(encoding="utf-8"))
        if record.get("status") not in {"pending_visual_review", "approved", "rejected"}:
            raise AssetCenterError("Transition de revue interdite.")
        record["status"] = decision
        record["human_approved"] = decision == "approved"
        record["review"] = {
            "decision": decision, "reviewer_id": reviewer,
            "evidence": evidence.strip(), "reviewed_at": _utc_now(),
        }
        _atomic_write(index_path, json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2).encode())
        return record
