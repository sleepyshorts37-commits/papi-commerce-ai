"""Production WSGI composition for the authenticated PAPI KIDS API."""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any, Callable

from .papi_kids_manuscript_api import create_papi_kids_manuscript_app
from .papi_kids_postgres_queue import (
    build_postgres_asset_reviewer,
    build_postgres_library_reader,
    build_postgres_queue_registrar,
    build_postgres_safety_reviewer,
    build_postgres_status_reader,
)
from .papi_kids_worker_service import create_postgres_connection_factory


def create_app(
    *,
    storage_root: str | Path | None = None,
    connection_factory: Callable[[], Any] | None = None,
) -> Callable[..., list[bytes]]:
    """Compose the WSGI API with private storage and PostgreSQL-only server callbacks."""
    configured_root = storage_root or os.environ.get("PAPI_KIDS_PRIVATE_STORAGE_DIR", "")
    if not configured_root:
        raise RuntimeError("PAPI_KIDS_PRIVATE_STORAGE_DIR absent.")
    raw_root = Path(configured_root)
    if raw_root.is_symlink():
        raise RuntimeError("Le volume privé ne peut pas être un lien symbolique.")
    root = raw_root.resolve()
    if root == Path("/") or root == Path.cwd().resolve():
        raise RuntimeError("Répertoire privé non sécurisé.")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)

    factory = connection_factory or create_postgres_connection_factory()
    inner_app = create_papi_kids_manuscript_app(
        storage_root=root,
        queue_registrar=build_postgres_queue_registrar(factory),
        status_reader=build_postgres_status_reader(factory),
        review_handler=build_postgres_asset_reviewer(factory),
        safety_review_handler=build_postgres_safety_reviewer(factory),
        library_reader=build_postgres_library_reader(factory),
    )

    def readiness_app(environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        if environ.get("PATH_INFO") != "/readyz":
            return inner_app(environ, start_response)
        if environ.get("REQUEST_METHOD") != "GET":
            body = b'{"status":"method_not_allowed"}'
            start_response("405 Method Not Allowed", [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
            ])
            return [body]

        storage_ready = (
            root.is_dir()
            and not raw_root.is_symlink()
            and stat.S_IMODE(root.stat().st_mode) == 0o700
            and os.access(root, os.W_OK | os.X_OK)
        )
        database_ready = False
        connection = None
        cursor = None
        try:
            connection = factory()
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
            database_ready = bool(row and row[0] == 1)
        except Exception:
            database_ready = False
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
        ready = storage_ready and database_ready
        payload = json.dumps({
            "status": "ready" if ready else "not_ready",
            "components": {
                "private_storage": storage_ready,
                "database": database_ready,
            },
        }, separators=(",", ":")).encode("utf-8")
        start_response(
            "200 OK" if ready else "503 Service Unavailable",
            [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(payload))),
                ("Cache-Control", "no-store"),
                ("X-Content-Type-Options", "nosniff"),
            ],
        )
        return [payload]

    return readiness_app


class LazyWSGIApplication:
    """Delay secret/config validation until the server receives its first request."""

    def __init__(self):
        self._application: Callable[..., list[bytes]] | None = None

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        if self._application is None:
            self._application = create_app()
        return self._application(environ, start_response)


app = LazyWSGIApplication()
