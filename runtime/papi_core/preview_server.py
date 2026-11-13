"""Loopback-only, read-only preview server for generated static websites."""
from __future__ import annotations

import ipaddress
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


class PreviewServerError(ValueError):
    """Raised when a preview server configuration is unsafe."""


class _PreviewHandler(BaseHTTPRequestHandler):
    server_version = "PapiPreview/1.0"
    sys_version = ""

    def do_POST(self) -> None:
        self.send_error(405, "Preview is read-only")

    do_PUT = do_POST
    do_PATCH = do_POST
    do_DELETE = do_POST

    def do_GET(self) -> None:
        self._serve(head_only=False)

    def do_HEAD(self) -> None:
        self._serve(head_only=True)

    def _serve(self, head_only: bool) -> None:
        parsed = urlsplit(self.path)
        try:
            decoded = unquote(parsed.path, errors="strict")
        except (UnicodeDecodeError, ValueError):
            self.send_error(400, "Invalid path")
            return
        if "\\" in decoded or "\x00" in decoded:
            self.send_error(400, "Invalid path")
            return
        relative = decoded.lstrip("/") or "index.html"
        candidate = Path(relative)
        if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
            self.send_error(403, "Path not allowed")
            return
        if decoded.endswith("/"):
            candidate = candidate / "index.html"
        root: Path = self.server.preview_root  # type: ignore[attr-defined]
        target = root / candidate
        try:
            resolved = target.resolve(strict=True)
            if root not in resolved.parents or not resolved.is_file():
                raise OSError("outside preview root")
            current = root
            for part in candidate.parts:
                current = current / part
                if current.is_symlink():
                    raise OSError("symlink not allowed")
            payload = resolved.read_bytes()
        except (OSError, RuntimeError):
            self.send_error(404, "Preview file not found")
            return
        content_type = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head_only:
            self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


class _PreviewHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def create_preview_server(
    site_root: str | Path, host: str = "127.0.0.1", port: int = 0
) -> ThreadingHTTPServer:
    """Create, but do not start, a loopback-only preview server."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise PreviewServerError("L'aperçu doit être lié à une adresse IP locale.") from exc
    if not address.is_loopback:
        raise PreviewServerError("L'aperçu ne peut écouter que sur loopback.")
    if not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535:
        raise PreviewServerError("Port invalide.")
    root = Path(site_root).resolve(strict=True)
    if not root.is_dir():
        raise PreviewServerError("Le répertoire d'aperçu est invalide.")
    server = _PreviewHTTPServer((host, port), _PreviewHandler)
    server.preview_root = root  # type: ignore[attr-defined]
    return server
