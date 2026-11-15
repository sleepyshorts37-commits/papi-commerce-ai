"""Explicit allowlist router for confirmed-free image models.

The router never discovers or enables models implicitly and never falls back to
paid providers. It minimizes estimated quota use per image, then measures the
observed batch throughput from real elapsed time and returned statuses.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import threading
import time
from typing import Any, Callable


class ImageModelRoutingError(ValueError):
    """Invalid free-model registry or routing request."""


_MODEL = re.compile(r"^@?[A-Za-z0-9][A-Za-z0-9._:/@-]{0,199}$")


@dataclass(frozen=True)
class FreeImageModel:
    model_id: str
    estimated_neurons_per_image: int
    free_confirmed: bool


def calculate_throughput(*, generated_images: int, elapsed_seconds: float) -> dict[str, float | int]:
    """Calculate observed throughput; never substitutes a synthetic benchmark."""
    if not isinstance(generated_images, int) or isinstance(generated_images, bool) or generated_images < 0:
        raise ImageModelRoutingError("Nombre d'images générées invalide.")
    if not isinstance(elapsed_seconds, (int, float)) or isinstance(elapsed_seconds, bool) or elapsed_seconds <= 0:
        raise ImageModelRoutingError("Durée réelle invalide.")
    return {
        "generated_images": generated_images,
        "elapsed_seconds": float(elapsed_seconds),
        "images_per_hour": generated_images * 3600.0 / float(elapsed_seconds),
    }


class FreeImageModelRouter:
    """Route every image to the cheapest explicitly confirmed-free model."""

    def __init__(
        self, *, provider: Any, models: list[FreeImageModel],
        max_batch_size: int = 500, clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not callable(getattr(provider, "generate_many", None)):
            raise ImageModelRoutingError("Adaptateur fournisseur incompatible.")
        if not isinstance(models, list) or not models:
            raise ImageModelRoutingError("Registre des modèles gratuits vide.")
        if not isinstance(max_batch_size, int) or isinstance(max_batch_size, bool) or not 1 <= max_batch_size <= 500:
            raise ImageModelRoutingError("Taille de lot invalide.")
        seen = set()
        for model in models:
            if not isinstance(model, FreeImageModel):
                raise ImageModelRoutingError("Entrée de registre modèle invalide.")
            if not isinstance(model.model_id, str) or not _MODEL.fullmatch(model.model_id):
                raise ImageModelRoutingError("Identifiant de modèle invalide.")
            if model.model_id in seen:
                raise ImageModelRoutingError("Modèle dupliqué dans le registre.")
            seen.add(model.model_id)
            if not isinstance(model.estimated_neurons_per_image, int) or isinstance(model.estimated_neurons_per_image, bool) or model.estimated_neurons_per_image <= 0:
                raise ImageModelRoutingError("Coût estimé par image invalide.")
            if model.free_confirmed is not True:
                raise ImageModelRoutingError("Modèle non confirmé gratuit : routage interdit.")
        self.provider = provider
        self.models = tuple(sorted(models, key=lambda item: (item.estimated_neurons_per_image, item.model_id)))
        self.max_batch_size = max_batch_size
        self.clock = clock
        self._metrics_lock = threading.Lock()
        self._last_metrics: dict[str, Any] | None = None

    @property
    def last_metrics(self) -> dict[str, Any] | None:
        with self._metrics_lock:
            return dict(self._last_metrics) if self._last_metrics else None

    def generate_many(self, *, jobs: list[dict[str, Any]], now: Any = None) -> list[dict[str, Any]]:
        if not isinstance(jobs, list) or not jobs:
            raise ImageModelRoutingError("Le lot doit contenir au moins une image.")
        if len(jobs) > self.max_batch_size:
            raise ImageModelRoutingError("Lot trop volumineux.")
        keys = set()
        selected = self.models[0]
        routed = []
        for index, job in enumerate(jobs):
            if not isinstance(job, dict):
                raise ImageModelRoutingError(f"Travail {index} invalide.")
            prompt, key = job.get("prompt"), job.get("idempotency_key")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ImageModelRoutingError(f"Prompt absent pour le travail {index}.")
            if not isinstance(key, str) or not key.strip() or key in keys:
                raise ImageModelRoutingError("Clé d'idempotence absente ou dupliquée.")
            keys.add(key)
            routed.append({
                "prompt": prompt,
                "model": selected.model_id,
                "idempotency_key": key,
                "book_id": job.get("book_id"),
                "page_id": job.get("page_id"),
                "page_number": job.get("page_number"),
                "batch_id": job.get("batch_id"),
            })
        started = self.clock()
        results = self.provider.generate_many(jobs=routed, now=now)
        elapsed = self.clock() - started
        if not isinstance(results, list) or len(results) != len(routed):
            raise ImageModelRoutingError("Résultats fournisseur incomplets ; rapprochement requis.")
        successful = sum(
            isinstance(result, dict)
            and result.get("status") == "generated"
            and result.get("idempotency_key") == routed[index]["idempotency_key"]
            for index, result in enumerate(results)
        )
        metrics = calculate_throughput(
            generated_images=successful,
            elapsed_seconds=max(float(elapsed), 1e-9),
        )
        metrics.update({
            "model_id": selected.model_id,
            "estimated_neurons_per_image": selected.estimated_neurons_per_image,
            "failed_or_uncertain_images": len(results) - successful,
            "paid_fallback_used": False,
        })
        with self._metrics_lock:
            self._last_metrics = metrics
        return results
