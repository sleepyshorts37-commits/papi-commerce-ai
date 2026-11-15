"""Single-job offline editorial worker backed by the PostgreSQL lease queue."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .papi_kids_editorial_queue import analyze_queued_manuscript
from .papi_kids_postgres_queue import (
    claim_editorial_job,
    complete_editorial_job,
    fail_editorial_job,
)


def run_one_editorial_job(
    connection_factory: Callable[[], Any],
    *,
    storage_root: str | Path,
    worker_id: str,
    lease_seconds: int = 300,
    retry_delay_seconds: int = 60,
) -> dict[str, Any]:
    """Claim and process at most one job; local deterministic scan only."""
    claimed = claim_editorial_job(
        connection_factory, worker_id=worker_id, lease_seconds=lease_seconds
    )
    if claimed is None:
        return {"status": "idle", "processed": False}
    job_id = claimed["job_id"]
    payload = claimed.get("payload") or {}
    upload_id = payload.get("upload_id")
    try:
        record = analyze_queued_manuscript(storage_root, upload_id)
        if record.get("status") not in {"analysis_ready", "needs_editor_review"}:
            raise ValueError("Analyse structurelle incomplète.")
        analysis = record.get("analysis") or {}
        if analysis.get("ai_invoked") is not False or analysis.get("provider_invoked") is not False:
            raise ValueError("L'analyse hors ligne a invoqué un fournisseur interdit.")
        complete_editorial_job(
            connection_factory,
            job_id=job_id,
            worker_id=worker_id,
            result=analysis,
            book_status=record["status"],
        )
        return {
            "status": "completed",
            "processed": True,
            "job_id": job_id,
            "upload_id": upload_id,
            "book_status": record["status"],
            "ai_invoked": False,
            "provider_invoked": False,
        }
    except Exception as exc:
        terminal_status = fail_editorial_job(
            connection_factory,
            job_id=job_id,
            worker_id=worker_id,
            error=f"{type(exc).__name__}: {exc}",
            retry_delay_seconds=retry_delay_seconds,
        )
        return {
            "status": terminal_status,
            "processed": True,
            "job_id": job_id,
            "upload_id": upload_id,
            "error_type": type(exc).__name__,
        }
