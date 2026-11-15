"""Authenticated, bounded WSGI endpoint for private PAPI KIDS manuscript intake."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib, hmac, json, os
from pathlib import Path
import re, uuid
from typing import Any, Callable

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
_ALLOWED_EXTENSIONS = {".md", ".txt"}

def _response(start_response: Callable[..., Any], status: str, payload: dict[str, Any]) -> list[bytes]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(status, [("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))), ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff")])
    return [body]

def create_papi_kids_manuscript_app(*, storage_root: str | Path | None = None,
        token_env: str = "PAPI_KIDS_UPLOAD_TOKEN",
        allow_insecure_local: bool = False) -> Callable[..., list[bytes]]:
    """Create WSGI app. Configure a random 32+ char token in server secrets."""
    def app(environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        if environ.get("PATH_INFO") != "/api/papi-kids/manuscripts":
            return _response(start_response, "404 Not Found", {"error": "not_found"})
        if environ.get("REQUEST_METHOD") != "POST":
            return _response(start_response, "405 Method Not Allowed", {"error": "method_not_allowed"})
        if environ.get("wsgi.url_scheme") != "https" and not allow_insecure_local:
            return _response(start_response, "403 Forbidden", {"error": "https_required"})
        configured_token = os.environ.get(token_env, "")
        if len(configured_token) < 32:
            return _response(start_response, "503 Service Unavailable", {"error": "server_not_configured"})
        supplied = environ.get("HTTP_AUTHORIZATION", "")
        if not supplied.startswith("Bearer ") or not hmac.compare_digest(supplied[7:], configured_token):
            return _response(start_response, "401 Unauthorized", {"error": "unauthorized"})
        filename = environ.get("HTTP_X_FILENAME", "")
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
        root = Path(storage_root or os.environ.get("PAPI_KIDS_PRIVATE_STORAGE_DIR", ""))
        if not str(root):
            return _response(start_response, "503 Service Unavailable", {"error": "storage_not_configured"})
        try:
            root.mkdir(parents=True, exist_ok=True)
            upload_id = "PKP-UP-" + uuid.uuid4().hex
            book_dir = root / upload_id
            book_dir.mkdir(mode=0o700)
            manuscript_path = book_dir / ("manuscript" + Path(filename).suffix.lower())
            temporary = book_dir / ".upload.tmp"
            temporary.write_bytes(raw)
            os.chmod(temporary, 0o600)
            temporary.replace(manuscript_path)
            metadata = {"upload_id": upload_id, "original_filename": filename,
                "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                "received_at": datetime.now(timezone.utc).isoformat(),
                "status": "received_pending_editorial_analysis", "storage_visibility": "private"}
            metadata_path = book_dir / "metadata.json"
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
            os.chmod(metadata_path, 0o600)
        except OSError:
            return _response(start_response, "500 Internal Server Error", {"error": "private_storage_failed"})
        return _response(start_response, "201 Created", {"upload_id": upload_id,
            "status": metadata["status"], "sha256": metadata["sha256"], "size_bytes": metadata["size_bytes"]})
    return app
