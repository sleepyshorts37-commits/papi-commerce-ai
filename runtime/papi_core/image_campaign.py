"""Multi-book image campaign planning and bounded execution for PAPI.

Planning is deterministic and offline. Execution is explicit, bounded per run,
and resumes safely by relying on deterministic image idempotency keys plus the
asset center's existing-asset checks. No scheduler or background worker is started.
"""
from __future__ import annotations

from typing import Any
import re

from .image_factory import ImageBatch, plan_book_images
from .image_production_engine import ImageProductionEngine

_CAMPAIGN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")


class ImageCampaignError(ValueError):
    """Invalid campaign definition or execution controls."""


def plan_image_campaign(
    *,
    campaign_id: str,
    books: list[dict[str, Any]],
    model: str,
    model_costs: dict[str, int],
    max_batch_size: int = 20,
    max_batch_units: int = 2_000,
    max_books: int = 100,
    max_total_pages: int = 10_000,
) -> dict[str, Any]:
    """Plan one campaign spanning multiple books, without network calls."""
    if not isinstance(campaign_id, str) or not _CAMPAIGN_ID.fullmatch(campaign_id):
        raise ImageCampaignError("Identifiant de campagne invalide.")
    if not isinstance(books, list) or not books or len(books) > max_books:
        raise ImageCampaignError("Nombre de livres invalide pour la campagne.")
    if not isinstance(max_total_pages, int) or isinstance(max_total_pages, bool) or max_total_pages < 1:
        raise ImageCampaignError("Limite totale de pages invalide.")

    seen_books: set[str] = set()
    batches: list[ImageBatch] = []
    total_pages = 0
    for book in books:
        if not isinstance(book, dict):
            raise ImageCampaignError("Chaque livre doit être un objet.")
        book_id = book.get("book_id")
        pages = book.get("pages")
        if not isinstance(book_id, str) or book_id in seen_books:
            raise ImageCampaignError("Identifiant de livre absent ou dupliqué.")
        if not isinstance(pages, list) or not pages:
            raise ImageCampaignError(f"Le livre {book_id} ne contient aucune page.")
        total_pages += len(pages)
        if total_pages > max_total_pages:
            raise ImageCampaignError("La campagne dépasse la limite totale de pages.")
        seen_books.add(book_id)
        batches.extend(plan_book_images(
            book_id=book_id, pages=pages, model=model, model_costs=model_costs,
            max_batch_size=max_batch_size, max_batch_units=max_batch_units,
        ))

    return {
        "schema_version": 1,
        "campaign_id": campaign_id,
        "book_count": len(seen_books),
        "page_count": total_pages,
        "batch_count": len(batches),
        "estimated_units": sum(batch.estimated_units for batch in batches),
        "model": model,
        "batches": batches,
    }


def execute_image_campaign(
    *,
    plan: dict[str, Any],
    engine: ImageProductionEngine,
    max_batches_per_run: int = 10,
    blocked_batch_ids: set[str] | None = None,
    start_batch_index: int = 0,
) -> dict[str, Any]:
    """Execute a bounded slice; rerun the same plan to resume stored assets.

    A batch with any failed or uncertain result is halted and returned for
    reconciliation. Pass its ID in blocked_batch_ids on a later run to prevent
    an accidental blind resubmission while other batches continue.
    """
    if not isinstance(plan, dict) or plan.get("schema_version") != 1:
        raise ImageCampaignError("Plan de campagne invalide.")
    batches = plan.get("batches")
    if not isinstance(batches, list) or not batches:
        raise ImageCampaignError("La campagne ne contient aucun lot.")
    if not isinstance(max_batches_per_run, int) or isinstance(max_batches_per_run, bool) or not 1 <= max_batches_per_run <= 100:
        raise ImageCampaignError("Nombre de lots par exécution invalide (1 à 100).")
    if not isinstance(start_batch_index, int) or isinstance(start_batch_index, bool) or not 0 <= start_batch_index <= len(batches):
        raise ImageCampaignError("Index de reprise invalide.")
    blocked = blocked_batch_ids or set()
    if not isinstance(blocked, set) or any(not isinstance(item, str) for item in blocked):
        raise ImageCampaignError("Liste des lots bloqués invalide.")

    reports: list[dict[str, Any]] = []
    executed = 0
    halted_batch_ids: list[str] = []
    skipped_blocked: list[str] = []
    next_batch_index = start_batch_index

    for index in range(start_batch_index, len(batches)):
        batch = batches[index]
        next_batch_index = index
        if batch.batch_id in blocked:
            skipped_blocked.append(batch.batch_id)
            continue
        if executed >= max_batches_per_run:
            break
        report = engine.execute_batch(batch)
        reports.append(report)
        executed += 1
        if report.get("failed_count", 0) or report.get("uncertain_count", 0):
            halted_batch_ids.append(batch.batch_id)
            next_batch_index = index + 1
            # Do not submit more batches until this result has been reconciled.
            break
        next_batch_index = index + 1
    else:
        next_batch_index = len(batches)

    complete = next_batch_index >= len(batches)
    return {
        "campaign_id": plan["campaign_id"],
        "book_count": plan["book_count"],
        "page_count": plan["page_count"],
        "planned_batch_count": len(batches),
        "executed_batch_count": executed,
        "next_batch_index": next_batch_index,
        "remaining_batch_count": max(0, len(batches) - next_batch_index),
        "complete": complete,
        "halted_batch_ids": halted_batch_ids,
        "skipped_blocked_batch_ids": skipped_blocked,
        "blocked_batch_ids_to_persist": sorted(blocked | set(halted_batch_ids)),
        "batch_reports": reports,
        "automatic_retries": 0,
        "human_reconciliation_required": bool(halted_batch_ids),
    }
