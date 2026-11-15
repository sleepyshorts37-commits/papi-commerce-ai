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
                select b.book_id, b.upload_id, b.status as book_status, b.created_at, b.updated_at,
                       j.job_id, j.status as job_status, j.attempts, j.max_attempts,
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
                    "status": values["job_status"],
                    "attempts": values["attempts"],
                    "max_attempts": values["max_attempts"],
                    "available_at": values["available_at"].isoformat() if values.get("available_at") else None,
                    "lease_until": values["lease_until"].isoformat() if values.get("lease_until") else None,
                }
            cursor.execute(
                """select asset_id, page_number, version, review_status, width_px, height_px, media_type
                     from papi_kids_private.illustration_assets
                    where book_id = %s
                    order by page_number, version desc""",
                (values["book_id"],),
            )
            asset_rows = cursor.fetchall()
            illustrations = [
                {"asset_id": row[0], "page_number": row[1], "version": row[2],
                 "review_status": row[3], "width_px": row[4], "height_px": row[5],
                 "media_type": row[6]}
                for row in asset_rows
            ]
            connection.commit()
            return {
                "upload_id": values["upload_id"],
                "book_status": values["book_status"],
                "created_at": values["created_at"].isoformat() if values.get("created_at") else None,
                "updated_at": values["updated_at"].isoformat() if values.get("updated_at") else None,
                "job": job,
                "illustrations": illustrations,
            }
        except Exception:
            connection.rollback()
            raise
        finally:
            close = getattr(connection, "close", None)
            if callable(close):
                close()
    return read_status



def register_illustration_asset(
    connection_factory: Callable[[], Any], metadata: dict[str, Any]
) -> dict[str, Any]:
    """Persist asset metadata and its initial audit event in one DB transaction."""
    required = ("asset_id", "upload_id", "page_number", "version", "sha256",
                "storage_key", "media_type", "width_px", "height_px")
    if not isinstance(metadata, dict) or any(key not in metadata for key in required):
        raise ValueError("Métadonnées d'illustration incomplètes.")
    if not _UPLOAD_ID.fullmatch(str(metadata["upload_id"])) or not _SHA256.fullmatch(str(metadata["sha256"])):
        raise ValueError("Référence ou empreinte d'illustration invalide.")
    connection = connection_factory()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "select book_id from papi_kids_private.books where upload_id = %s for update",
            (metadata["upload_id"],),
        )
        book = cursor.fetchone()
        if not book:
            raise PostgresEditorialQueueError("Livre parent introuvable.")
        book_id = book[0]
        cursor.execute(
            """
            insert into papi_kids_private.illustration_assets(
                asset_id, book_id, page_number, version, source_sha256, storage_key,
                media_type, width_px, height_px, source_provider, model_id,
                prompt_sha256, generation_ref, metadata
            ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
            on conflict (source_sha256) do nothing
            returning asset_id
            """,
            (
                metadata["asset_id"], book_id, metadata["page_number"], metadata["version"],
                metadata["sha256"], metadata["storage_key"], metadata["media_type"],
                metadata["width_px"], metadata["height_px"], metadata.get("source_provider"),
                metadata.get("model_id"), metadata.get("prompt_sha256"),
                metadata.get("generation_ref"),
                json.dumps({"review_status": "pending_review", "human_approval_required": True}),
            ),
        )
        inserted = cursor.fetchone()
        if inserted:
            asset_id = inserted[0]
            cursor.execute(
                """insert into papi_kids_private.illustration_review_events
                    (asset_id, event_type, actor, details)
                    values (%s, 'uploaded', 'papi-kids-intake', %s::jsonb)""",
                (asset_id, json.dumps({"upload_id": metadata["upload_id"], "page_number": metadata["page_number"]})),
            )
        else:
            cursor.execute(
                """select asset_id, book_id, page_number, version
                     from papi_kids_private.illustration_assets where source_sha256 = %s""",
                (metadata["sha256"],),
            )
            existing = cursor.fetchone()
            if not existing or (existing[1], existing[2], existing[3]) != (
                book_id, metadata["page_number"], metadata["version"]
            ):
                raise PostgresEditorialQueueError("Collision de version ou de contenu d'illustration.")
            asset_id = existing[0]
        connection.commit()
        return {"asset_id": asset_id, "book_id": str(book_id), "review_status": "pending_review"}
    except Exception:
        connection.rollback()
        raise
    finally:
        close = getattr(connection, "close", None)
        if callable(close):
            close()


def build_postgres_asset_registrar(connection_factory: Callable[[], Any]) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Build the server-side asset registrar callback."""
    def register(metadata: dict[str, Any]) -> dict[str, Any]:
        return register_illustration_asset(connection_factory, metadata)
    return register



def review_illustration_asset(
    connection_factory: Callable[[], Any], *, asset_id: str, decision: str,
    reviewer_id: str, notes: str = "",
) -> dict[str, Any]:
    """Record a human approval/rejection and supersede older approved page versions."""
    if not isinstance(asset_id, str) or not re.fullmatch(r"PKP-ASSET-[0-9a-f]{24}", asset_id):
        raise ValueError("Identifiant d'illustration invalide.")
    if decision not in {"approved", "rejected"}:
        raise ValueError("Décision de revue invalide.")
    if not isinstance(reviewer_id, str) or not 3 <= len(reviewer_id) <= 120:
        raise ValueError("Identifiant du réviseur invalide.")
    if not isinstance(notes, str) or len(notes) > 1000:
        raise ValueError("Commentaire de revue trop long.")
    connection = connection_factory()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """select book_id, page_number, review_status
                 from papi_kids_private.illustration_assets
                where asset_id = %s for update""",
            (asset_id,),
        )
        asset = cursor.fetchone()
        if not asset:
            raise PostgresEditorialQueueError("Illustration introuvable.")
        book_id, page_number, current_status = asset
        if current_status == decision:
            connection.commit()
            return {"asset_id": asset_id, "review_status": decision, "reviewer_id": reviewer_id}
        if current_status == "superseded":
            raise PostgresEditorialQueueError("Cette version a été remplacée.")
        if decision == "approved":
            cursor.execute(
                """update papi_kids_private.illustration_assets
                      set review_status = 'superseded'
                    where book_id = %s and page_number = %s
                      and review_status = 'approved' and asset_id <> %s
                  returning asset_id""",
                (book_id, page_number, asset_id),
            )
            for row in cursor.fetchall():
                cursor.execute(
                    """insert into papi_kids_private.illustration_review_events
                        (asset_id, event_type, actor, details)
                        values (%s, 'superseded', %s, %s::jsonb)""",
                    (row[0], reviewer_id, json.dumps({"reason": "newer_version_approved"})),
                )
        cursor.execute(
            """update papi_kids_private.illustration_assets
                  set review_status = %s, reviewed_at = now(), reviewed_by = %s
                where asset_id = %s and review_status in ('pending_review','rejected')
              returning asset_id""",
            (decision, reviewer_id, asset_id),
        )
        if not cursor.fetchone():
            raise PostgresEditorialQueueError("Transition de revue non autorisée.")
        cursor.execute(
            """insert into papi_kids_private.illustration_review_events
                (asset_id, event_type, actor, details)
                values (%s, %s, %s, %s::jsonb)""",
            (asset_id, decision, reviewer_id, json.dumps({"notes": notes})),
        )
        connection.commit()
        return {"asset_id": asset_id, "review_status": decision, "reviewer_id": reviewer_id}
    except Exception:
        connection.rollback()
        raise
    finally:
        close = getattr(connection, "close", None)
        if callable(close):
            close()


def build_postgres_asset_reviewer(connection_factory: Callable[[], Any]) -> Callable[..., dict[str, Any]]:
    """Build the server-side human-review callback."""
    def review(asset_id: str, decision: str, reviewer_id: str, notes: str = "") -> dict[str, Any]:
        return review_illustration_asset(
            connection_factory, asset_id=asset_id, decision=decision,
            reviewer_id=reviewer_id, notes=notes,
        )
    return review
