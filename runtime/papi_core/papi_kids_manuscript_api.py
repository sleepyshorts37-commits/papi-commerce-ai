"""Authenticated, bounded WSGI endpoint for private PAPI KIDS manuscript intake."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib, hmac, json, os
from pathlib import Path
import re, tempfile
from urllib.parse import unquote
from typing import Any, Callable

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
_UPLOAD_ID = re.compile(r"^PKP-UP-[0-9a-f]{32}$")
_ALLOWED_EXTENSIONS = {".md", ".txt"}

def _response(start_response: Callable[..., Any], status: str, payload: dict[str, Any]) -> list[bytes]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(status, [("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))), ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff")])
    return [body]

def _save_metadata(book_dir: Path, metadata: dict[str, Any]) -> None:
    fd, temporary_name = tempfile.mkstemp(prefix=".metadata-", suffix=".tmp", dir=book_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(metadata, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, book_dir / "metadata.json")
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def _register_queue(book_dir: Path, metadata: dict[str, Any],
                    queue_registrar: Callable[[dict[str, Any]], dict[str, Any]] | None) -> str | None:
    if queue_registrar is None:
        metadata.setdefault("persistence_status", "local_only")
        return None
    try:
        registered = queue_registrar(metadata)
        if not isinstance(registered, dict) or not registered.get("job_id"):
            raise ValueError("Réponse PostgreSQL invalide.")
        metadata["persistence_status"] = "registered"
        metadata["postgres_queue"] = {
            "book_id": registered.get("book_id"),
            "job_id": registered["job_id"],
            "status": registered.get("status", "queued_for_analysis"),
        }
        _save_metadata(book_dir, metadata)
        return None
    except Exception:
        metadata["persistence_status"] = "pending_retry"
        _save_metadata(book_dir, metadata)
        return "database_queue_unavailable"


def create_papi_kids_manuscript_app(*, storage_root: str | Path | None = None,
        token_env: str = "PAPI_KIDS_UPLOAD_TOKEN",
        allow_insecure_local: bool = False,
        queue_registrar: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        status_reader: Callable[[str], dict[str, Any] | None] | None = None,
        review_handler: Callable[[str, str, str, str], dict[str, Any]] | None = None,
        review_token_env: str = "PAPI_KIDS_REVIEW_TOKEN",
        safety_review_token_env: str = "PAPI_KIDS_SAFETY_REVIEW_TOKEN",
        safety_review_handler: Callable[[str, str, str, str, str], dict[str, Any]] | None = None,
        metadata_token_env: str = "PAPI_KIDS_METADATA_TOKEN",
        metadata_saver: Callable[[str, dict[str, Any], str], dict[str, Any]] | None = None,
        metadata_editor_id_env: str = "PAPI_KIDS_METADATA_EDITOR_ID",
        reviewer_id_env: str = "PAPI_KIDS_REVIEWER_ID",
        library_reader: Callable[[], list[dict[str, Any]]] | None = None) -> Callable[..., list[bytes]]:
    """Create WSGI app. Configure a random 32+ char token in server secrets."""
    def app(environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        request_path = environ.get("PATH_INFO", "")
        if request_path == "/healthz":
            if environ.get("REQUEST_METHOD") != "GET":
                return _response(start_response, "405 Method Not Allowed", {"error": "method_not_allowed"})
            return _response(start_response, "200 OK", {"status": "ok", "service": "papi-kids"})
        upload_route = request_path == "/api/papi-kids/manuscripts"
        status_match = re.fullmatch(r"/api/papi-kids/manuscripts/(PKP-UP-[0-9a-f]{32})", request_path)
        review_match = re.fullmatch(r"/api/papi-kids/assets/(PKP-ASSET-[0-9a-f]{24})/review", request_path)
        safety_review_match = re.fullmatch(r"/api/papi-kids/manuscripts/(PKP-UP-[0-9a-f]{32})/safety-review", request_path)
        metadata_match = re.fullmatch(r"/api/papi-kids/manuscripts/(PKP-UP-[0-9a-f]{32})/kdp-metadata", request_path)
        if not upload_route and not status_match and not review_match and not safety_review_match and not metadata_match:
            return _response(start_response, "404 Not Found", {"error": "not_found"})
        request_method = environ.get("REQUEST_METHOD")
        expected_method = "POST" if review_match or safety_review_match or metadata_match or (upload_route and request_method == "POST") else "GET"
        if request_method != expected_method:
            return _response(start_response, "405 Method Not Allowed", {"error": "method_not_allowed"})
        if environ.get("wsgi.url_scheme") != "https" and not allow_insecure_local:
            return _response(start_response, "403 Forbidden", {"error": "https_required"})
        selected_token_env = (
            metadata_token_env if metadata_match else
            (safety_review_token_env if safety_review_match else
             (review_token_env if review_match else token_env))
        )
        configured_token = os.environ.get(selected_token_env, "")
        if len(configured_token) < 32:
            return _response(start_response, "503 Service Unavailable", {"error": "server_not_configured"})
        supplied = environ.get("HTTP_AUTHORIZATION", "")
        if not supplied.startswith("Bearer ") or not hmac.compare_digest(supplied[7:], configured_token):
            return _response(start_response, "401 Unauthorized", {"error": "unauthorized"})
        if upload_route and request_method == "GET":
            if library_reader is None:
                return _response(start_response, "503 Service Unavailable", {"error": "library_not_configured"})
            try:
                books = library_reader()
            except Exception:
                return _response(start_response, "503 Service Unavailable", {"error": "library_unavailable"})
            return _response(start_response, "200 OK", {"books": books})
        if review_match:
            if review_handler is None:
                return _response(start_response, "503 Service Unavailable", {"error": "review_not_configured"})
            reviewer_id = os.environ.get(reviewer_id_env, "")
            if len(reviewer_id) < 3 or len(reviewer_id) > 120:
                return _response(start_response, "503 Service Unavailable", {"error": "reviewer_not_configured"})
            if environ.get("CONTENT_TYPE", "").split(";", 1)[0].strip().lower() != "application/json":
                return _response(start_response, "415 Unsupported Media Type", {"error": "json_required"})
            try:
                review_length = int(environ.get("CONTENT_LENGTH") or "0")
            except (TypeError, ValueError):
                review_length = 0
            if review_length < 1 or review_length > 4096:
                return _response(start_response, "413 Payload Too Large", {"error": "invalid_review_size"})
            try:
                review_payload = json.loads(environ["wsgi.input"].read(review_length).decode("utf-8"))
            except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
                return _response(start_response, "400 Bad Request", {"error": "invalid_review_json"})
            if not isinstance(review_payload, dict) or review_payload.get("decision") not in {"approved", "rejected"}:
                return _response(start_response, "400 Bad Request", {"error": "invalid_review_decision"})
            notes = review_payload.get("notes", "")
            if not isinstance(notes, str) or len(notes) > 1000:
                return _response(start_response, "400 Bad Request", {"error": "invalid_review_notes"})
            try:
                reviewed = review_handler(review_match.group(1), review_payload["decision"], reviewer_id, notes)
            except ValueError:
                return _response(start_response, "400 Bad Request", {"error": "invalid_review"})
            except Exception:
                return _response(start_response, "409 Conflict", {"error": "review_transition_rejected"})
            return _response(start_response, "200 OK", reviewed)
        if metadata_match:
            if metadata_saver is None:
                return _response(start_response, "503 Service Unavailable", {"error": "metadata_saver_not_configured"})
            editor_id = os.environ.get(metadata_editor_id_env, "")
            if len(editor_id.strip()) < 3 or len(editor_id.strip()) > 120:
                return _response(start_response, "503 Service Unavailable", {"error": "metadata_editor_not_configured"})
            if environ.get("CONTENT_TYPE", "").split(";", 1)[0].strip().lower() != "application/json":
                return _response(start_response, "415 Unsupported Media Type", {"error": "json_required"})
            try:
                metadata_length = int(environ.get("CONTENT_LENGTH") or "0")
            except (TypeError, ValueError):
                metadata_length = 0
            if metadata_length < 1 or metadata_length > 20000:
                return _response(start_response, "413 Payload Too Large", {"error": "invalid_metadata_size"})
            try:
                metadata_payload = json.loads(environ["wsgi.input"].read(metadata_length).decode("utf-8"))
            except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
                return _response(start_response, "400 Bad Request", {"error": "invalid_metadata_json"})
            metadata = metadata_payload.get("metadata") if isinstance(metadata_payload, dict) else None
            if not isinstance(metadata, dict):
                return _response(start_response, "400 Bad Request", {"error": "metadata_object_required"})
            try:
                saved = metadata_saver(
                    metadata_match.group(1), metadata, editor_id.strip()
                )
            except ValueError:
                return _response(start_response, "400 Bad Request", {"error": "invalid_metadata"})
            except Exception:
                return _response(start_response, "409 Conflict", {"error": "metadata_save_rejected"})
            return _response(start_response, "200 OK", saved)
        if safety_review_match:
            if safety_review_handler is None:
                return _response(start_response, "503 Service Unavailable", {"error": "safety_review_not_configured"})
            reviewer_id = os.environ.get(reviewer_id_env, "")
            if len(reviewer_id) < 3 or len(reviewer_id) > 120:
                return _response(start_response, "503 Service Unavailable", {"error": "reviewer_not_configured"})
            if environ.get("CONTENT_TYPE", "").split(";", 1)[0].strip().lower() != "application/json":
                return _response(start_response, "415 Unsupported Media Type", {"error": "json_required"})
            try:
                review_length = int(environ.get("CONTENT_LENGTH") or "0")
            except (TypeError, ValueError):
                review_length = 0
            if review_length < 1 or review_length > 8192:
                return _response(start_response, "413 Payload Too Large", {"error": "invalid_review_size"})
            try:
                safety_payload = json.loads(environ["wsgi.input"].read(review_length).decode("utf-8"))
            except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
                return _response(start_response, "400 Bad Request", {"error": "invalid_review_json"})
            decision = safety_payload.get("decision") if isinstance(safety_payload, dict) else None
            manuscript_sha256 = safety_payload.get("manuscript_sha256") if isinstance(safety_payload, dict) else None
            notes = safety_payload.get("notes", "") if isinstance(safety_payload, dict) else ""
            if decision not in {"approved", "rejected"} or not isinstance(manuscript_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", manuscript_sha256):
                return _response(start_response, "400 Bad Request", {"error": "invalid_safety_review"})
            if not isinstance(notes, str) or len(notes) > 2000:
                return _response(start_response, "400 Bad Request", {"error": "invalid_review_notes"})
            try:
                reviewed = safety_review_handler(
                    safety_review_match.group(1), manuscript_sha256, decision, reviewer_id, notes
                )
            except ValueError:
                return _response(start_response, "400 Bad Request", {"error": "invalid_safety_review"})
            except Exception:
                return _response(start_response, "409 Conflict", {"error": "safety_review_transition_rejected"})
            return _response(start_response, "200 OK", reviewed)
        if status_match:
            if status_reader is None:
                return _response(start_response, "503 Service Unavailable", {"error": "status_not_configured"})
            try:
                status_record = status_reader(status_match.group(1))
            except Exception:
                return _response(start_response, "503 Service Unavailable", {"error": "status_unavailable"})
            if status_record is None:
                return _response(start_response, "404 Not Found", {"error": "manuscript_not_found"})
            return _response(start_response, "200 OK", status_record)
        filename = unquote(environ.get("HTTP_X_FILENAME", ""))
        if (not isinstance(filename, str) or len(filename) > 180 or Path(filename).name != filename
            or Path(filename).suffix.lower() not in _ALLOWED_EXTENSIONS
            or not re.fullmatch(r"[\w .()\-]+", filename, flags=re.UNICODE)):
            return _response(start_response, "400 Bad Request", {"error": "invalid_filename"})
        content_type = environ.get("CONTENT_TYPE", "").split(";", 1)[0].strip().lower()
        if content_type not in {"text/plain", "text/markdown"}:
            return _response(start_response, "415 Unsupported Media Type", {"error": "unsupported_media_type"})
        try:
            length = int(environ.get("CONTENT_LENGTH") or "0")
        except (TypeError, ValueError):
            length = 0
        if length < 1 or length > MAX_UPLOAD_BYTES:
            return _response(start_response, "413 Payload Too Large", {"error": "invalid_size"})
        stream = environ.get("wsgi.input")
        raw = stream.read(length) if stream is not None else b""
        if len(raw) != length:
            return _response(start_response, "400 Bad Request", {"error": "incomplete_upload"})
        try:
            manuscript = raw.decode("utf-8")
        except UnicodeDecodeError:
            return _response(start_response, "400 Bad Request", {"error": "invalid_utf8"})
        if not manuscript.strip():
            return _response(start_response, "400 Bad Request", {"error": "empty_manuscript"})
        root_value = storage_root or os.environ.get("PAPI_KIDS_PRIVATE_STORAGE_DIR")
        if not root_value:
            return _response(start_response, "503 Service Unavailable", {"error": "storage_not_configured"})
        root = Path(root_value)
        try:
            root.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256(raw).hexdigest()
            upload_id = "PKP-UP-" + digest[:32]
            book_dir = root / upload_id
            if book_dir.exists():
                existing = json.loads((book_dir / "metadata.json").read_text(encoding="utf-8"))
                if existing.get("sha256") != digest:
                    raise OSError("upload identifier collision")
                queue_error = _register_queue(book_dir, existing, queue_registrar)
                if queue_error:
                    return _response(start_response, "503 Service Unavailable", {
                        "error": queue_error, "upload_id": upload_id, "retryable": True})
                return _response(start_response, "200 OK", {"upload_id": upload_id,
                    "status": existing.get("status", "queued_for_analysis"),
                    "sha256": digest, "size_bytes": len(raw), "deduplicated": True,
                    "persistence_status": existing.get("persistence_status", "local_only")})
            import shutil, tempfile
            staging = Path(tempfile.mkdtemp(prefix=".papi-kids-intake-", dir=root))
            os.chmod(staging, 0o700)
            manuscript_name = "manuscript" + Path(filename).suffix.lower()
            manuscript_path = staging / manuscript_name
            manuscript_path.write_bytes(raw)
            os.chmod(manuscript_path, 0o600)
            received_at = datetime.now(timezone.utc).isoformat()
            metadata = {"upload_id": upload_id, "original_filename": filename,
                "size_bytes": len(raw), "sha256": digest, "received_at": received_at,
                "status": "queued_for_analysis", "storage_visibility": "private"}
            job = {"upload_id": upload_id, "job_type": "editorial_structure_analysis",
                "status": "queued_for_analysis", "stored_filename": manuscript_name,
                "source_sha256": digest, "attempts": 0, "created_at": received_at,
                "updated_at": received_at, "ai_invoked": False, "provider_invoked": False}
            for name, payload in (("metadata.json", metadata), ("job.json", job)):
                target = staging / name
                target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                os.chmod(target, 0o600)
            try:
                os.rename(staging, book_dir)
            except OSError:
                if book_dir.is_dir():
                    existing = json.loads((book_dir / "metadata.json").read_text(encoding="utf-8"))
                    if existing.get("sha256") == digest:
                        shutil.rmtree(staging, ignore_errors=True)
                        queue_error = _register_queue(book_dir, existing, queue_registrar)
                        if queue_error:
                            return _response(start_response, "503 Service Unavailable", {
                                "error": queue_error, "upload_id": upload_id, "retryable": True})
                        return _response(start_response, "200 OK", {"upload_id": upload_id,
                            "status": existing.get("status", "queued_for_analysis"),
                            "sha256": digest, "size_bytes": len(raw), "deduplicated": True,
                            "persistence_status": existing.get("persistence_status", "local_only")})
                raise
        except (OSError, ValueError, json.JSONDecodeError):
            if "staging" in locals():
                shutil.rmtree(staging, ignore_errors=True)
            return _response(start_response, "500 Internal Server Error", {"error": "private_storage_failed"})
        queue_error = _register_queue(book_dir, metadata, queue_registrar)
        if queue_error:
            return _response(start_response, "503 Service Unavailable", {
                "error": queue_error, "upload_id": upload_id, "retryable": True})
        return _response(start_response, "201 Created", {"upload_id": upload_id,
            "status": metadata["status"], "sha256": metadata["sha256"], "size_bytes": metadata["size_bytes"],
            "persistence_status": metadata.get("persistence_status", "local_only")})
    return app
