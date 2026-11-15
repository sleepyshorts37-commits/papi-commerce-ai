"""Human-readable PKP-0001 editorial preview and durable approval."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
from datetime import datetime, timezone
from typing import Any, Callable


class EditorialApprovalError(ValueError):
    """Editorial preview or approval is invalid."""


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _source_dir(project_root: str | Path | None) -> Path:
    root = Path(project_root or Path(__file__).resolve().parents[2]).resolve()
    candidate = root / "publishing" / "papi-kids" / "PKP-0001"
    if candidate.is_dir():
        return candidate
    if os.environ.get("PAPI_KIDS_BUNDLED_SOURCES", "").lower() == "true":
        bundled = Path(__file__).parent / "resources" / "PKP-0001"
        if bundled.is_dir():
            return bundled
    raise EditorialApprovalError("Sources éditoriales PKP-0001 absentes.")


def build_pkp0001_editorial_preview_reader(
    storage_root: str | Path,
    *,
    project_root: str | Path | None = None,
) -> Callable[[str], dict[str, Any]]:
    root = Path(storage_root).resolve()

    def read_preview(upload_id: str) -> dict[str, Any]:
        if not isinstance(upload_id, str) or not re.fullmatch(r"PKP-UP-[0-9a-f]{32}", upload_id):
            raise EditorialApprovalError("Référence de dépôt invalide.")
        book_dir = (root / upload_id).resolve()
        if book_dir.parent != root or not book_dir.is_dir() or book_dir.is_symlink():
            raise EditorialApprovalError("Dossier privé du manuscrit absent.")
        metadata_path = book_dir / "metadata.json"
        job_path = book_dir / "job.json"
        if metadata_path.is_symlink() or job_path.is_symlink():
            raise EditorialApprovalError("Métadonnées privées non sûres.")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        job = json.loads(job_path.read_text(encoding="utf-8"))
        if metadata.get("upload_id") != upload_id or job.get("upload_id") != upload_id:
            raise EditorialApprovalError("Références de dépôt incohérentes.")
        filename = job.get("stored_filename")
        if not isinstance(filename, str) or Path(filename).name != filename or filename in {"", ".", ".."}:
            raise EditorialApprovalError("Nom de manuscrit stocké invalide.")
        manuscript_path = book_dir / filename
        if manuscript_path.is_symlink() or not manuscript_path.is_file() or manuscript_path.parent != book_dir:
            raise EditorialApprovalError("Manuscrit privé absent.")
        uploaded_bytes = manuscript_path.read_bytes()
        uploaded_sha = _sha256(uploaded_bytes)
        if uploaded_sha != metadata.get("sha256") or uploaded_sha != job.get("source_sha256"):
            raise EditorialApprovalError("Empreinte du manuscrit reçu incohérente.")

        source_dir = _source_dir(project_root)
        names = {
            "manuscript": "manuscript-v2.md",
            "character_bible": "character-bible-v1.md",
            "storyboard": "storyboard-v1.md",
            "illustration_prompts": "illustration-prompts-24-v1.md",
        }
        sources = {}
        hashes = {}
        for key, name in names.items():
            path = source_dir / name
            if path.is_symlink() or not path.is_file():
                raise EditorialApprovalError(f"Source éditoriale absente : {name}.")
            raw = path.read_bytes()
            hashes[key + "_sha256"] = _sha256(raw)
            sources[key] = raw.decode("utf-8")

        prompt_text = sources["illustration_prompts"]
        headings = list(re.finditer(r"^###\s*(\d{1,2})\s*[—-]\s*(.+)$", prompt_text, re.MULTILINE))
        prompts = []
        for index, match in enumerate(headings):
            end = headings[index + 1].start() if index + 1 < len(headings) else len(prompt_text)
            prompt = prompt_text[match.end():end].strip()
            prompts.append({
                "page_number": int(match.group(1)),
                "title": match.group(2).strip(),
                "prompt": prompt,
                "sha256": _sha256(prompt.encode("utf-8")),
            })
        page_numbers = [item["page_number"] for item in prompts]
        prompts_valid = page_numbers == list(range(1, 25)) and all(item["prompt"] for item in prompts)
        bundle_hash = _sha256(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        canonical_manuscript_sha = hashes["manuscript_sha256"]
        source_match = uploaded_sha == canonical_manuscript_sha
        analysis_status = job.get("status", metadata.get("status", "unknown"))
        approval_eligible = source_match and prompts_valid and analysis_status == "analysis_ready"
        title_match = re.search(r"^#\s+(.+)$", sources["manuscript"], re.MULTILINE)
        return {
            "upload_id": upload_id,
            "book_id": "PKP-0001",
            "title": title_match.group(1).strip() if title_match else "PKP-0001",
            "analysis_status": analysis_status,
            "uploaded_manuscript_sha256": uploaded_sha,
            "canonical_manuscript_sha256": canonical_manuscript_sha,
            "source_match": source_match,
            "source_bundle_sha256": bundle_hash,
            "source_hashes": hashes,
            "page_count": len(prompts),
            "prompts_valid": prompts_valid,
            "approval_eligible": approval_eligible,
            "character_bible": sources["character_bible"],
            "storyboard": sources["storyboard"],
            "prompts": prompts,
            "warnings": [] if approval_eligible else [
                "Le manuscrit doit correspondre exactement à la V2 PKP-0001 et l'analyse éditoriale doit être prête avant approbation."
            ],
        }

    return read_preview


def build_postgres_editorial_approval_handler(
    connection_factory: Callable[[], Any],
    *,
    preview_reader: Callable[[str], dict[str, Any]],
    storage_root: str | Path,
    reviewer_id: str,
) -> Callable[[str, dict[str, Any]], dict[str, Any]]:
    root = Path(storage_root).resolve()
    if not isinstance(reviewer_id, str) or not 3 <= len(reviewer_id) <= 120:
        raise EditorialApprovalError("Identifiant du réviseur absent ou invalide.")

    def approve(upload_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict) or payload.get("approved") is not True:
            raise EditorialApprovalError("L'approbation doit être explicitement confirmée.")
        preview = preview_reader(upload_id)
        if not preview.get("approval_eligible"):
            raise EditorialApprovalError("Le plan éditorial n'est pas admissible à l'approbation.")
        if payload.get("source_bundle_sha256") != preview["source_bundle_sha256"]:
            raise EditorialApprovalError("Le plan a changé depuis sa consultation ; rechargez l'aperçu.")
        approval = {
            "approved": True,
            "upload_id": upload_id,
            "book_id": "PKP-0001",
            "source_bundle_sha256": preview["source_bundle_sha256"],
            "manuscript_sha256": preview["uploaded_manuscript_sha256"],
            "reviewer_id": reviewer_id,
            "approved_at": datetime.now(timezone.utc).isoformat(),
        }
        connection = connection_factory()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                update papi_kids_private.books
                   set metadata = jsonb_set(coalesce(metadata, '{}'::jsonb),
                       '{editorial_approval}', %s::jsonb, true),
                       updated_at = now()
                 where upload_id = %s
                returning book_id
                """,
                (json.dumps(approval), upload_id),
            )
            row = cursor.fetchone()
            if not row:
                connection.rollback()
                raise EditorialApprovalError("Livre absent du registre PostgreSQL.")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

        book_dir = (root / upload_id).resolve()
        if book_dir.parent != root or not book_dir.is_dir():
            raise EditorialApprovalError("Dossier privé du manuscrit absent après validation.")
        metadata_path = book_dir / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["editorial_approval"] = approval
        temporary = book_dir / "metadata.json.approval.tmp"
        temporary.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, metadata_path)
        return approval

    return approve


def build_postgres_editorial_approval_reader(
    connection_factory: Callable[[], Any],
) -> Callable[[str], dict[str, Any] | None]:
    def read_approval(upload_id: str) -> dict[str, Any] | None:
        connection = connection_factory()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "select metadata->'editorial_approval' from papi_kids_private.books where upload_id = %s",
                (upload_id,),
            )
            row = cursor.fetchone()
            if not row or not row[0]:
                return None
            value = row[0]
            return json.loads(value) if isinstance(value, str) else value
        finally:
            cursor.close()
            connection.close()
    return read_approval
