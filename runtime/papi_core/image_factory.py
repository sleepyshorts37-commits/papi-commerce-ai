"""Deterministic planning and asset manifests for PAPI IMAGE FACTORY.

Planning is offline. Provider calls happen only when execute_batch is explicitly
invoked with an already configured adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import re
from typing import Any

IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")
PRIORITY = {"urgent": 0, "high": 1, "normal": 2, "low": 3}


class ImageFactoryError(ValueError):
    """Invalid image production brief, plan or provider result."""


@dataclass(frozen=True)
class PlannedImage:
    book_id: str
    page_id: str
    page_number: int
    prompt: str
    model: str
    estimated_units: int
    idempotency_key: str
    priority: str

    def as_job(self) -> dict[str, str]:
        return {
            "prompt": self.prompt,
            "model": self.model,
            "idempotency_key": self.idempotency_key,
        }


@dataclass(frozen=True)
class ImageBatch:
    batch_id: str
    book_id: str
    model: str
    estimated_units: int
    jobs: tuple[PlannedImage, ...]

    def as_provider_jobs(self) -> list[dict[str, str]]:
        return [job.as_job() for job in self.jobs]


def _required_identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ImageFactoryError(f"{field} invalide.")
    return value


def _stable_key(book_id: str, page_id: str, model: str, prompt: str) -> str:
    digest = hashlib.sha256(
        "\x1f".join((book_id, page_id, model, prompt)).encode("utf-8")
    ).hexdigest()
    return f"papi-image:{digest}"


def plan_book_images(
    *,
    book_id: str,
    pages: list[dict[str, Any]],
    model: str,
    model_costs: dict[str, int],
    max_batch_size: int = 20,
    max_batch_units: int = 2_000,
) -> list[ImageBatch]:
    """Create deterministic, quota-aware batches without network access."""
    book = _required_identifier(book_id, "book_id")
    if not isinstance(model, str) or model not in model_costs:
        raise ImageFactoryError("Modèle absent du registre de coûts autorisés.")
    unit_cost = model_costs[model]
    if not isinstance(unit_cost, int) or isinstance(unit_cost, bool) or unit_cost <= 0:
        raise ImageFactoryError("Coût estimé du modèle invalide.")
    if not isinstance(pages, list) or not pages:
        raise ImageFactoryError("Le livre doit contenir au moins une page.")
    if not isinstance(max_batch_size, int) or isinstance(max_batch_size, bool) or not 1 <= max_batch_size <= 100:
        raise ImageFactoryError("Taille de lot invalide (1 à 100).")
    if not isinstance(max_batch_units, int) or isinstance(max_batch_units, bool) or max_batch_units < unit_cost:
        raise ImageFactoryError("Budget estimé par lot insuffisant ou invalide.")

    planned: list[PlannedImage] = []
    seen_page_ids: set[str] = set()
    seen_page_numbers: set[int] = set()
    for page in pages:
        if not isinstance(page, dict):
            raise ImageFactoryError("Chaque page doit être un objet.")
        page_id = _required_identifier(page.get("page_id"), "page_id")
        page_number = page.get("page_number")
        prompt = page.get("prompt")
        priority = page.get("priority", "normal")
        if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
            raise ImageFactoryError("Numéro de page invalide.")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 12_000:
            raise ImageFactoryError("Prompt vide ou trop long.")
        if priority not in PRIORITY:
            raise ImageFactoryError("Priorité inconnue.")
        if page_id in seen_page_ids or page_number in seen_page_numbers:
            raise ImageFactoryError("Identifiant ou numéro de page dupliqué.")
        seen_page_ids.add(page_id)
        seen_page_numbers.add(page_number)
        prompt_clean = prompt.strip()
        planned.append(PlannedImage(
            book_id=book, page_id=page_id, page_number=page_number,
            prompt=prompt_clean, model=model, estimated_units=unit_cost,
            idempotency_key=_stable_key(book, page_id, model, prompt_clean),
            priority=priority,
        ))

    planned.sort(key=lambda item: (PRIORITY[item.priority], item.page_number))
    batches: list[ImageBatch] = []
    current: list[PlannedImage] = []
    current_units = 0

    def flush() -> None:
        nonlocal current, current_units
        if not current:
            return
        first = current[0]
        seed = "|".join(item.idempotency_key for item in current)
        batch_digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]
        batches.append(ImageBatch(
            batch_id=f"batch-{book}-{batch_digest}", book_id=book,
            model=model, estimated_units=current_units, jobs=tuple(current),
        ))
        current, current_units = [], 0

    for item in planned:
        if current and (
            len(current) >= max_batch_size
            or current_units + item.estimated_units > max_batch_units
        ):
            flush()
        current.append(item)
        current_units += item.estimated_units
    flush()
    return batches


def execute_image_batch(
    adapter: Any, batch: ImageBatch, *, now: datetime | None = None
) -> list[dict[str, Any]]:
    """Explicitly submit one planned batch; never retries failures automatically."""
    method = getattr(adapter, "generate_many", None)
    if not callable(method):
        raise ImageFactoryError("Adaptateur incompatible : generate_many requis.")
    results = method(jobs=batch.as_provider_jobs(), now=now)
    if not isinstance(results, list) or len(results) != len(batch.jobs):
        raise ImageFactoryError("Le fournisseur n'a pas retourné un résultat par image.")
    return results


def build_asset_manifest(
    *, book_id: str, batch: ImageBatch, results: list[dict[str, Any]]
) -> dict[str, Any]:
    """Create a metadata-only manifest; image bytes are never copied into JSON."""
    if book_id != batch.book_id:
        raise ImageFactoryError("Le livre ne correspond pas au lot.")
    if not isinstance(results, list) or len(results) != len(batch.jobs):
        raise ImageFactoryError("Nombre de résultats différent du nombre de pages.")
    assets: list[dict[str, Any]] = []
    for planned, result in zip(batch.jobs, results):
        if not isinstance(result, dict):
            raise ImageFactoryError("Résultat d'image invalide.")
        status = result.get("status")
        record: dict[str, Any] = {
            "book_id": book_id,
            "page_id": planned.page_id,
            "page_number": planned.page_number,
            "model": planned.model,
            "idempotency_key": planned.idempotency_key,
            "status": "pending_visual_review" if status == "generated" else "generation_failed",
            "human_approved": False,
        }
        if status == "generated":
            image_bytes = result.get("image_bytes")
            if not isinstance(image_bytes, bytes) or not image_bytes:
                raise ImageFactoryError("Image générée sans octets exploitables.")
            record["content_sha256"] = hashlib.sha256(image_bytes).hexdigest()
            record["byte_length"] = len(image_bytes)
            record["mime_type"] = result.get("mime_type", "image/unknown")
        assets.append(record)
    return {
        "schema_version": 1,
        "book_id": book_id,
        "batch_id": batch.batch_id,
        "model": batch.model,
        "asset_count": len(assets),
        "generated_count": sum(a["status"] == "pending_visual_review" for a in assets),
        "failed_count": sum(a["status"] == "generation_failed" for a in assets),
        "assets": assets,
    }
