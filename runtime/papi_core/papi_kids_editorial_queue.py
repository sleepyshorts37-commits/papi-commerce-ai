"""Private, durable PAPI KIDS editorial queue and deterministic offline analysis."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from .papi_kids_safety_review import analyze_child_safety, PapiKidsSafetyReviewError

_UPLOAD_ID = re.compile(r"^PKP-UP-[0-9a-f]{32}$")
_HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*#*\s*$", re.MULTILINE)


class EditorialQueueError(ValueError):
    """Invalid or unavailable manuscript queue record."""


def _book_dir(storage_root: str | Path, upload_id: str) -> Path:
    if not isinstance(upload_id, str) or not _UPLOAD_ID.fullmatch(upload_id):
        raise EditorialQueueError("Référence de dépôt invalide.")
    root = Path(storage_root).resolve()
    folder = (root / upload_id).resolve()
    if folder.parent != root:
        raise EditorialQueueError("Chemin de dépôt invalide.")
    return folder


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    fd, temporary_name = tempfile.mkstemp(prefix=".queue-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, path)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def get_queue_record(storage_root: str | Path, upload_id: str) -> dict[str, Any]:
    folder = _book_dir(storage_root, upload_id)
    try:
        record = json.loads((folder / "job.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EditorialQueueError("Travail éditorial introuvable ou illisible.") from exc
    if record.get("upload_id") != upload_id:
        raise EditorialQueueError("Référence de travail incohérente.")
    return record


def analyze_queued_manuscript(storage_root: str | Path, upload_id: str) -> dict[str, Any]:
    """Run deterministic local structure inspection only; never calls an AI/provider."""
    folder = _book_dir(storage_root, upload_id)
    record = get_queue_record(storage_root, upload_id)
    if record.get("status") != "queued_for_analysis":
        return record
    manuscript_name = record.get("stored_filename")
    if manuscript_name not in {"manuscript.md", "manuscript.txt"}:
        raise EditorialQueueError("Nom de manuscrit stocké invalide.")
    try:
        source = (folder / manuscript_name).read_text(encoding="utf-8")
    except OSError as exc:
        raise EditorialQueueError("Manuscrit privé inaccessible.") from exc
    headings = [match.group(2).strip() for match in _HEADING.finditer(source)]
    page_headings = list(re.finditer(r"^###\s+Page\s+(\d+)\s+[—-]", source, re.MULTILINE | re.IGNORECASE))
    safety_screening: dict[str, Any] = {
        "status": "not_run_unstructured_manuscript",
        "automatic_approval": False,
        "human_review_required": True,
    }
    safety_flagged = False
    if page_headings:
        try:
            safety_screening = analyze_child_safety(source, expected_pages=len(page_headings))
            safety_flagged = safety_screening["issue_count"] > 0
        except PapiKidsSafetyReviewError as exc:
            safety_screening = {
                "status": "needs_manual_safety_review",
                "error_type": type(exc).__name__,
                "automatic_approval": False,
                "human_review_required": True,
            }
            safety_flagged = True
    now = datetime.now(timezone.utc).isoformat()
    record.update({
        "status": "analysis_ready" if headings and not safety_flagged else "needs_editor_review",
        "analysis": {
            "method": "deterministic_offline_structure_scan",
            "ai_invoked": False,
            "provider_invoked": False,
            "section_count": len(headings),
            "sections": headings[:200],
            "character_count": len(source),
            "completed_at": now,
            "editorial_approval_required": True,
            "child_safety_screening": safety_screening,
        },
        "updated_at": now,
    })
    _atomic_json(folder / "job.json", record)
    metadata_path = folder / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["status"] = record["status"]
    metadata["analysis_completed_at"] = now
    _atomic_json(metadata_path, metadata)
    return record
