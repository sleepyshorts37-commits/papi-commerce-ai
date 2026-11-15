"""Append-only audit trail for image quality reviews.

Stores immutable JSON events on a private persistent volume. Automated review
outcomes are recorded separately from explicit human approval decisions.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any


class ImageQualityAuditError(ValueError):
    """Invalid audit event or storage operation."""


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_ALLOWED_STATUSES = {"blocked", "awaiting_visual_review", "pending_human_approval"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _atomic_create(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".papi-audit-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        # Atomic create-if-absent: never overwrite a previously recorded event.
        os.link(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


class ImageQualityAuditLog:
    """Persist immutable automated-review events on a private durable volume."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()

    def append(
        self, *, event_id: str, book_id: str, page_id: str,
        content_sha256: str, report: dict[str, Any],
    ) -> dict[str, Any]:
        for value, field in ((event_id, "event_id"), (book_id, "book_id"), (page_id, "page_id")):
            if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
                raise ImageQualityAuditError(f"{field} invalide.")
        if not isinstance(content_sha256, str) or not _SHA256.fullmatch(content_sha256):
            raise ImageQualityAuditError("Empreinte SHA-256 invalide.")
        if not isinstance(report, dict) or report.get("status") not in _ALLOWED_STATUSES:
            raise ImageQualityAuditError("Rapport qualité absent ou statut non autorisé.")
        if report.get("content_sha256") != content_sha256:
            raise ImageQualityAuditError("Le rapport ne correspond pas à l'empreinte de l'image.")
        if report.get("human_approved") is not False or report.get("approval_required") is not True:
            raise ImageQualityAuditError("Un rapport automatisé ne peut pas approuver une image.")

        event = {
            "schema_version": 1,
            "event_id": event_id,
            "book_id": book_id,
            "page_id": page_id,
            "content_sha256": content_sha256,
            "reviewer_kind": "automated",
            "recorded_at": _utc_now(),
            "report": report,
            "human_approval_granted": False,
        }
        path = self.root / "events" / f"{event_id}.json"
        payload = json.dumps(event, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        try:
            _atomic_create(path, payload)
            return event
        except FileExistsError:
            existing = json.loads(path.read_text(encoding="utf-8"))
            candidate = dict(event)
            candidate["recorded_at"] = existing.get("recorded_at")
            if _canonical(candidate) != _canonical(existing):
                raise ImageQualityAuditError("event_id déjà utilisé pour un événement différent.")
            return existing

    def list_events(self, *, book_id: str, page_id: str | None = None) -> list[dict[str, Any]]:
        if not isinstance(book_id, str) or not _SAFE_ID.fullmatch(book_id):
            raise ImageQualityAuditError("book_id invalide.")
        if page_id is not None and (not isinstance(page_id, str) or not _SAFE_ID.fullmatch(page_id)):
            raise ImageQualityAuditError("page_id invalide.")
        directory = self.root / "events"
        events = []
        for path in sorted(directory.glob("*.json")) if directory.exists() else []:
            event = json.loads(path.read_text(encoding="utf-8"))
            if event.get("book_id") == book_id and (page_id is None or event.get("page_id") == page_id):
                events.append(event)
        return events
