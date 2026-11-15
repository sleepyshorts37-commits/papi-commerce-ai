"""DB-API adapter for the private PostgreSQL PAPI KIDS editorial queue.

The caller supplies a server-side PostgreSQL connection factory. This module
never creates network connections, reads secrets, or invokes AI/image vendors.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable

_UPLOAD_ID = re.compile(r"^PKP-UP-[0-9a-f]{32}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class PostgresEditorialQueueError(RuntimeError):
    """A durable editorial queue operation failed or lost its lease."""


def _validate(upload_id: str, source_sha256: str) -> None:
    if not isinstance(upload_id, str) or not _UPLOAD_ID.fullmatch(upload_id):
        raise ValueError("Référence de dépôt invalide.")
    if not isinstance(source_sha256, str) or not _SHA256.fullmatch(source_sha256):
        raise ValueError("Empreinte SHA-256 invalide.")


def enqueue_manuscript(
    connection_factory: Callable[[], Any],
    *,
    upload_id: str,
    source_sha256: str,
    original_filename: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Atomically register a book and one analysis job; safe to retry."""
    _validate(upload_id, source_sha256)
    if not isinstance(original_filename, str) or not original_filename or len(original_filename) > 180:
        raise ValueError("Nom de fichier invalide.")
    connection = connection_factory()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            insert into papi_kids_private.books
                (upload_id, source_sha256, original_filename, status, metadata)
            values (%s, %s, %s, 'queued_for_analysis', %s::jsonb)
            on conflict (source_sha256) do nothing
            """,
            (upload_id, source_sha256, original_filename, json.dumps(metadata or {}, ensure_ascii=False)),
        )
        cursor.execute(
            """
            select book_id, upload_id, status
              from papi_kids_private.books
             where source_sha256 = %s
             for update
            """,
            (source_sha256,),
        )
        book = cursor.fetchone()
        if not book:
            raise PostgresEditorialQueueError("Livre non enregistré.")
        book_id, persisted_upload_id, status = book
        if persisted_upload_id != upload_id:
            raise PostgresEditorialQueueError("Collision entre références de dépôt.")
        cursor.execute(
            """
            insert into papi_kids_private.editorial_jobs
                (book_id, job_type, status, payload)
            values (%s, 'editorial_structure_analysis', 'queued', %s::jsonb)
            on conflict (book_id, job_type) do nothing
            returning job_id
            """,
            (book_id, json.dumps({"upload_id": upload_id, "source_sha256": source_sha256})),
        )
        job = cursor.fetchone()
        if job:
            job_id = job[0]
        else:
            cursor.execute(
                """select job_id from papi_kids_private.editorial_jobs
                    where book_id = %s and job_type = 'editorial_structure_analysis'""",
                (book_id,),
            )
            existing = cursor.fetchone()
            if not existing:
                raise PostgresEditorialQueueError("Travail éditorial non créé.")
            job_id = existing[0]
        cursor.execute(
            """insert into papi_kids_private.editorial_job_events
                (job_id, event_type, details)
                values (%s, 'manuscript_registered', %s::jsonb)
                on conflict do nothing""",
            (job_id, json.dumps({"upload_id": upload_id})),
        )
        connection.commit()
        return {"book_id": str(book_id), "upload_id": upload_id, "job_id": job_id, "status": status}
    except Exception:
        connection.rollback()
        raise
    finally:
        close = getattr(connection, "close", None)
        if callable(close):
            close()


def claim_editorial_job(
    connection_factory: Callable[[], Any], *, worker_id: str, lease_seconds: int = 300
) -> dict[str, Any] | None:
    """Claim one job atomically; PostgreSQL SKIP LOCKED supports concurrent workers."""
    if not isinstance(worker_id, str) or not 3 <= len(worker_id) <= 120:
        raise ValueError("Identifiant worker invalide.")
    connection = connection_factory()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "select * from papi_kids_private.claim_editorial_job(%s, %s)",
            (worker_id, lease_seconds),
        )
        row = cursor.fetchone()
        connection.commit()
        if row is None:
            return None
        columns = [item[0] for item in cursor.description]
        return dict(zip(columns, row))
    except Exception:
        connection.rollback()
        raise
    finally:
        close = getattr(connection, "close", None)
        if callable(close):
            close()


def complete_editorial_job(
    connection_factory: Callable[[], Any], *, job_id: int, worker_id: str,
    result: dict[str, Any], book_status: str,
) -> None:
    """Complete only the currently leased job and persist its result and audit event."""
    if book_status not in {"analysis_ready", "needs_editor_review"}:
        raise ValueError("Statut éditorial final invalide.")
    connection = connection_factory()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            update papi_kids_private.editorial_jobs
               set status = 'completed', payload = payload || %s::jsonb,
                   lease_owner = null, lease_until = null, updated_at = now()
             where job_id = %s and status = 'processing' and lease_owner = %s
            returning book_id
            """,
            (json.dumps({"analysis": result}, ensure_ascii=False), job_id, worker_id),
        )
        row = cursor.fetchone()
        if not row:
            raise PostgresEditorialQueueError("Bail expiré ou worker non propriétaire ; résultat refusé.")
        cursor.execute(
            "update papi_kids_private.books set status = %s, updated_at = now() where book_id = %s",
            (book_status, row[0]),
        )
        cursor.execute(
            """insert into papi_kids_private.editorial_job_events
                (job_id, event_type, worker_id, details)
                values (%s, 'completed', %s, %s::jsonb)""",
            (job_id, worker_id, json.dumps({"book_status": book_status})),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        close = getattr(connection, "close", None)
        if callable(close):
            close()


def fail_editorial_job(
    connection_factory: Callable[[], Any], *, job_id: int, worker_id: str,
    error: str, retry_delay_seconds: int = 60,
) -> str:
    """Record a failure and requeue until max_attempts, then mark terminally failed."""
    connection = connection_factory()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            update papi_kids_private.editorial_jobs
               set status = case when attempts >= max_attempts then 'failed' else 'queued' end,
                   available_at = now() + make_interval(secs => greatest(1, least(%s, 86400))),
                   lease_owner = null, lease_until = null,
                   last_error = left(%s, 2000), updated_at = now()
             where job_id = %s and status = 'processing' and lease_owner = %s
            returning status, book_id
            """,
            (retry_delay_seconds, error, job_id, worker_id),
        )
        row = cursor.fetchone()
        if not row:
            raise PostgresEditorialQueueError("Bail expiré ou worker non propriétaire ; échec refusé.")
        status, book_id = row
        if status == "failed":
            cursor.execute(
                "update papi_kids_private.books set status = 'failed', updated_at = now() where book_id = %s",
                (book_id,),
            )
        cursor.execute(
            """insert into papi_kids_private.editorial_job_events
                (job_id, event_type, worker_id, details)
                values (%s, %s, %s, %s::jsonb)""",
            (job_id, status, worker_id, json.dumps({"error": error[:2000]})),
        )
        connection.commit()
        return status
    except Exception:
        connection.rollback()
        raise
    finally:
        close = getattr(connection, "close", None)
        if callable(close):
            close()



def build_postgres_queue_registrar(connection_factory: Callable[[], Any]) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Build the WSGI intake callback; keep the connection factory server-side."""
    def register(metadata: dict[str, Any]) -> dict[str, Any]:
        return enqueue_manuscript(
            connection_factory,
            upload_id=metadata["upload_id"],
            source_sha256=metadata["sha256"],
            original_filename=metadata["original_filename"],
            metadata={
                "size_bytes": metadata.get("size_bytes"),
                "received_at": metadata.get("received_at"),
                "storage_visibility": "private",
            },
        )
    return register



def build_postgres_status_reader(connection_factory: Callable[[], Any]) -> Callable[[str], dict[str, Any] | None]:
    """Build a read-only status callback that returns no manuscript text or secrets."""
    def read_status(upload_id: str) -> dict[str, Any] | None:
        if not isinstance(upload_id, str) or not _UPLOAD_ID.fullmatch(upload_id):
            raise ValueError("Référence de dépôt invalide.")
        connection = connection_factory()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                select b.upload_id, b.status, b.created_at, b.updated_at,
                       j.job_id, j.status, j.attempts, j.max_attempts,
                       j.available_at, j.lease_until
                  from papi_kids_private.books b
                  left join papi_kids_private.editorial_jobs j on j.book_id = b.book_id
                 where b.upload_id = %s
                """,
                (upload_id,),
            )
            row = cursor.fetchone()
            if row is None:
                connection.commit()
                return None
            names = [item[0] for item in cursor.description]
            values = dict(zip(names, row))
            job = None
            if values.get("job_id") is not None:
                job = {
                    "job_id": values["job_id"],
                    "status": values["status"],
                    "attempts": values["attempts"],
                    "max_attempts": values["max_attempts"],
                    "available_at": values["available_at"].isoformat() if values.get("available_at") else None,
                    "lease_until": values["lease_until"].isoformat() if values.get("lease_until") else None,
                }
            connection.commit()
            return {
                "upload_id": values["upload_id"],
                "book_status": values["status"],
                "created_at": values["created_at"].isoformat() if values.get("created_at") else None,
                "updated_at": values["updated_at"].isoformat() if values.get("updated_at") else None,
                "job": job,
            }
        except Exception:
            connection.rollback()
            raise
        finally:
            close = getattr(connection, "close", None)
            if callable(close):
                close()
    return read_status
