"""Orchestrate planned image jobs through provider and durable asset store.

The engine is deliberately adapter-driven: tests use fakes, and no provider call
occurs unless execute_batch is explicitly invoked by the application.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
from typing import Any


class ImageProductionError(RuntimeError):
    """Invalid production request or incompatible adapter."""


class ImageProductionEngine:
    """Resume-safe coordinator for planner batches, generator and asset center."""

    def __init__(self, *, generator: Any, asset_center: Any, max_batch_size: int = 500):
        if not callable(getattr(generator, "generate_many", None)):
            raise ImageProductionError("Adaptateur de génération incompatible.")
        if not callable(getattr(asset_center, "get", None)) or not callable(getattr(asset_center, "put", None)):
            raise ImageProductionError("Centre d'assets incompatible.")
        if not isinstance(max_batch_size, int) or isinstance(max_batch_size, bool) or not 1 <= max_batch_size <= 500:
            raise ImageProductionError("Taille maximale de lot invalide.")
        self.generator = generator
        self.asset_center = asset_center
        self.max_batch_size = max_batch_size

    def execute_batch(self, batch: Any, *, now: datetime | None = None) -> dict[str, Any]:
        jobs = getattr(batch, "jobs", None)
        book_id = getattr(batch, "book_id", None)
        if not isinstance(book_id, str) or not isinstance(jobs, tuple) or not jobs:
            raise ImageProductionError("Lot planifié invalide ou vide.")
        if len(jobs) > self.max_batch_size:
            raise ImageProductionError("Lot supérieur à la limite de l'orchestrateur.")

        pending = []
        outcomes: dict[str, dict[str, Any]] = {}
        for planned in jobs:
            existing = self.asset_center.get(
                book_id=planned.book_id, page_id=planned.page_id,
                idempotency_key=planned.idempotency_key,
            )
            if existing is not None:
                outcomes[planned.idempotency_key] = {
                    "status": "already_stored", "asset": existing,
                }
            else:
                pending.append(planned)

        provider_results: list[dict[str, Any]] = []
        if pending:
            payload = [{
                "prompt": item.prompt, "model": item.model,
                "idempotency_key": item.idempotency_key,
                "book_id": item.book_id,
                "page_id": item.page_id,
                "page_number": item.page_number,
                "batch_id": batch.batch_id,
            } for item in pending]
            provider_results = self.generator.generate_many(jobs=payload, now=now)
            if not isinstance(provider_results, list) or len(provider_results) != len(pending):
                raise ImageProductionError(
                    "Le fournisseur n'a pas retourné exactement un résultat par image ; "
                    "état à rapprocher avant toute relance."
                )

        for planned, result in zip(pending, provider_results):
            if not isinstance(result, dict) or result.get("idempotency_key") != planned.idempotency_key:
                outcomes[planned.idempotency_key] = {
                    "status": "result_mismatch",
                    "error": "Résultat fournisseur non corrélé ; aucune nouvelle tentative automatique.",
                }
                continue
            if result.get("status") != "generated":
                outcomes[planned.idempotency_key] = {
                    "status": "generation_failed",
                    "error": str(result.get("error", "Échec fournisseur sans détail."))[:500],
                }
                continue
            image_bytes = result.get("image_bytes")
            if not isinstance(image_bytes, bytes) or not image_bytes:
                outcomes[planned.idempotency_key] = {
                    "status": "generated_without_bytes",
                    "error": "Réponse annoncée comme générée mais octets absents ; rapprochement requis.",
                }
                continue
            try:
                asset = self.asset_center.put(
                    book_id=planned.book_id, page_id=planned.page_id,
                    page_number=planned.page_number,
                    idempotency_key=planned.idempotency_key,
                    image_bytes=image_bytes,
                    content_type=result.get("content_type"),
                    model=planned.model,
                    prompt_sha256=hashlib.sha256(planned.prompt.encode("utf-8")).hexdigest(),
                )
            except Exception as exc:
                # Provider may already have charged quota. Do not blindly call it again.
                outcomes[planned.idempotency_key] = {
                    "status": "persistence_uncertain",
                    "error": f"Image reçue mais sauvegarde échouée : {str(exc)[:300]}",
                    "quota_reconciliation_required": True,
                }
                continue
            outcomes[planned.idempotency_key] = {"status": "stored", "asset": asset}

        ordered = [outcomes[item.idempotency_key] for item in jobs]
        counts = {key: sum(item["status"] == key for item in ordered) for key in (
            "stored", "already_stored", "generation_failed", "result_mismatch",
            "generated_without_bytes", "persistence_uncertain",
        )}
        return {
            "batch_id": getattr(batch, "batch_id", None),
            "book_id": book_id,
            "planned_count": len(jobs),
            "provider_submissions": len(pending),
            "stored_count": counts["stored"],
            "skipped_existing_count": counts["already_stored"],
            "failed_count": counts["generation_failed"],
            "uncertain_count": counts["result_mismatch"] + counts["generated_without_bytes"] + counts["persistence_uncertain"],
            "outcomes": ordered,
            "automatic_retries": 0,
            "human_review_required": True,
        }
