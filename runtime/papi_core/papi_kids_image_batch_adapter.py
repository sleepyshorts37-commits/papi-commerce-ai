"""Batch adapter bridging guarded Cloudflare FLUX to the generic image router."""
from __future__ import annotations

from typing import Any

from .papi_kids_image_provider import CloudflareFluxSchnellProvider, ImageProviderBlocked, MODEL_ID


class CloudflareFluxSchnellBatchAdapter:
    def __init__(
        self,
        *,
        provider: CloudflareFluxSchnellProvider,
        quota_evidence: dict[str, Any],
        generation_authorized: bool = False,
    ):
        self.provider = provider
        self.quota_evidence = quota_evidence
        self.generation_authorized = generation_authorized is True
        self.ledger = provider.reservation_store
        self.model_costs = {MODEL_ID: 58}
        self.account_id = provider.account_id

    def authorize_generation(self, approved: bool) -> None:
        if approved is not True:
            raise ImageProviderBlocked("Autorisation de génération non confirmée.")
        self.generation_authorized = True

    def generate_many(self, *, jobs: list[dict[str, Any]], now: Any = None) -> list[dict[str, Any]]:
        if not isinstance(jobs, list) or not jobs:
            raise ImageProviderBlocked("Lot de génération vide.")
        results = []
        blocked = False
        for job in jobs:
            key = job.get("idempotency_key") if isinstance(job, dict) else None
            if not isinstance(key, str):
                raise ImageProviderBlocked("Clé d'idempotence absente du travail.")
            if blocked:
                results.append({
                    "status": "failed", "idempotency_key": key,
                    "error": "Lot arrêté après le premier refus ; aucun autre appel fournisseur.",
                })
                continue
            if job.get("model") != MODEL_ID:
                blocked = True
                results.append({
                    "status": "failed", "idempotency_key": key,
                    "error": "Modèle différent du modèle Cloudflare autorisé.",
                })
                continue
            try:
                generated = self.provider.generate(
                    job.get("prompt", ""),
                    evidence=self.quota_evidence,
                    allow_generation=self.generation_authorized,
                    campaign_id=job.get("batch_id") or "",
                    page_number=job.get("page_number"),
                )
                results.append({
                    "status": "generated",
                    "idempotency_key": key,
                    "image_bytes": generated["image_bytes"],
                    "content_type": generated["media_type"],
                    "provider": generated["provider"],
                    "model_id": generated["model_id"],
                    "width_px": generated["width_px"],
                    "height_px": generated["height_px"],
                    "estimated_neurons": generated["estimated_neurons"],
                    "cost_minor": generated["cost_minor"],
                    "print_ready_300dpi": generated["print_ready_300dpi"],
                    "fallback_used": False,
                })
            except Exception as exc:
                blocked = True
                results.append({
                    "status": "failed",
                    "idempotency_key": key,
                    "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                    "fallback_used": False,
                })
        return results
