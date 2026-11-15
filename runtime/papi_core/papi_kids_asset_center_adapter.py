"""Asset-center adapter that persists provider output into the private PAPI KIDS store."""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Callable

from .papi_kids_asset_store import store_illustration_asset


class PapiKidsIllustrationAssetCenter:
    def __init__(self, storage_root: str | Path, *, upload_id: str,
                 asset_registrar: Callable[[dict[str, Any]], Any],
                 logical_book_id: str = "PKP-0001"):
        self.root = Path(storage_root).resolve()
        self.upload_id = upload_id
        self.logical_book_id = logical_book_id
        self.asset_registrar = asset_registrar
        if not self.root.is_dir():
            raise ValueError("Volume privé PAPI KIDS absent.")
        if not re.fullmatch(r"PKP-UP-[0-9a-f]{32}", upload_id):
            raise ValueError("Référence de dépôt invalide.")
        if not re.fullmatch(r"PKP-[A-Z0-9-]{1,40}", logical_book_id):
            raise ValueError("Identifiant logique de livre invalide.")
        if not (self.root / upload_id).is_dir():
            raise ValueError("Dossier privé du manuscrit absent.")

    def _book_dir(self, book_id: str) -> Path:
        if book_id not in {self.logical_book_id, self.upload_id}:
            raise ValueError("Le moteur a fourni un identifiant de livre non associé au dépôt.")
        path = (self.root / self.upload_id).resolve()
        if path.parent != self.root or not path.is_dir():
            raise ValueError("Dossier privé du manuscrit absent.")
        return path

    def _records(self, upload_id: str, page_number: int) -> list[tuple[int, Path, dict[str, Any]]]:
        folder = self._book_dir(upload_id) / "illustrations"
        records = []
        if not folder.exists():
            return records
        for metadata_path in folder.glob(f"page-{page_number:02d}-v*.json"):
            match = re.search(r"-v(\d{3})\.json$", metadata_path.name)
            if not match:
                continue
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            records.append((int(match.group(1)), metadata_path, metadata))
        return sorted(records, key=lambda item: item[0])

    def get(self, *, book_id: str, page_id: str, page_number: int,
            idempotency_key: str) -> dict[str, Any] | None:
        records = self._records(book_id, page_number)
        for version, metadata_path, metadata in reversed(records):
            if metadata.get("idempotency_key") != idempotency_key:
                continue
            if metadata.get("persistence_status") == "registered":
                # Reconcile the private sidecar with PostgreSQL before skipping generation.
                self.asset_registrar(metadata)
                return metadata
            storage_path = (self.root / metadata["storage_key"]).resolve()
            if self.root not in storage_path.parents or not storage_path.is_file():
                raise ValueError("Asset orphelin : rapprochement manuel requis.")
            image_bytes = storage_path.read_bytes()
            retried = store_illustration_asset(
                self.root, upload_id=self.upload_id, page_number=page_number, version=version,
                image_bytes=image_bytes, media_type=metadata["media_type"],
                source_provider=metadata.get("source_provider"),
                model_id=metadata.get("model_id"),
                prompt_sha256=metadata.get("prompt_sha256"),
                generation_ref=metadata.get("generation_ref"),
                idempotency_key=idempotency_key,
                source_width_px=metadata.get("source_width_px"),
                source_height_px=metadata.get("source_height_px"),
                upscaling_method=metadata.get("upscaling_method", "native"),
                resolution_review=metadata.get("resolution_review"),
                asset_registrar=self.asset_registrar,
            )
            if retried.get("persistence_status") != "registered":
                raise ValueError("Enregistrement PostgreSQL toujours incertain.")
            return retried
        # An image without its sidecar must never be blindly regenerated.
        folder = self._book_dir(book_id) / "illustrations"
        if folder.exists():
            known_stems = {item[1].stem for item in records}
            image_files = list(folder.glob(f"page-{page_number:02d}-v*.png")) + list(folder.glob(f"page-{page_number:02d}-v*.jpg")) + list(folder.glob(f"page-{page_number:02d}-v*.webp"))
            if any(path.stem not in known_stems for path in image_files):
                raise ValueError("Fichier d'illustration sans métadonnées ; rapprochement requis.")
        return None

    def put(self, *, book_id: str, page_id: str, page_number: int,
            idempotency_key: str, image_bytes: bytes, content_type: str | None,
            model: str, prompt_sha256: str | None) -> dict[str, Any]:
        records = self._records(book_id, page_number)
        version = (records[-1][0] + 1) if records else 1
        if version > 1000:
            raise ValueError("Limite de versions d'illustration atteinte.")
        stored = store_illustration_asset(
            self.root, upload_id=self.upload_id, page_number=page_number, version=version,
            image_bytes=image_bytes, media_type=(content_type or ""),
            source_provider="cloudflare_workers_ai", model_id=model,
            prompt_sha256=prompt_sha256, generation_ref=idempotency_key,
            idempotency_key=idempotency_key,
            asset_registrar=self.asset_registrar,
        )
        if stored.get("persistence_status") != "registered":
            raise ValueError("Image sauvegardée localement, registre PostgreSQL incertain.")
        return stored
