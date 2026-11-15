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
    build_postgres_kdp_metadata_saver,
    build_postgres_kdp_package_reviewer,
    build_postgres_kindle_previewer_reviewer,
    build_postgres_kdp_owner_release_authorizer,
    build_postgres_status_reader,
)
from .papi_kids_worker_service import create_postgres_connection_factory
from .papi_kids_mobile_dashboard import render_papi_kids_mobile_dashboard
from .papi_kids_kdp_build_service import (
    build_private_kdp_package_handler,
    build_private_kdp_package_downloader,
)
from .papi_kids_readiness import check_papi_kids_readiness


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
        metadata_saver=build_postgres_kdp_metadata_saver(factory),
        kdp_build_handler=build_private_kdp_package_handler(storage_root, factory),
        kdp_package_review_handler=build_postgres_kdp_package_reviewer(factory),
        kindle_previewer_handler=build_postgres_kindle_previewer_reviewer(factory),
        kdp_package_download_handler=build_private_kdp_package_downloader(storage_root, factory),
        readiness_handler=lambda: check_papi_kids_readiness(
            storage_root=storage_root, connection_factory=factory,
        ),
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

    dashboard_book_id = os.environ.get("PAPI_KIDS_DASHBOARD_BOOK_ID", "PKP-0001")
    dashboard_title = os.environ.get("PAPI_KIDS_DASHBOARD_TITLE", "Nia et la rivière aux mille reflets")
    try:
        dashboard_page_count = int(os.environ.get("PAPI_KIDS_DASHBOARD_PAGE_COUNT", "24"))
    except ValueError as exc:
        raise RuntimeError("PAPI_KIDS_DASHBOARD_PAGE_COUNT invalide.") from exc
    dashboard_scenes = [
        {"page_number": number, "heading": f"Page {number}",
         "detail": "À préparer", "status": "not_started"}
        for number in range(1, dashboard_page_count + 1)
    ]
    dashboard_html = render_papi_kids_mobile_dashboard(
        book_id=dashboard_book_id, title=dashboard_title,
        page_count=dashboard_page_count, scenes=dashboard_scenes,
        overall_status="Prêt à recevoir le manuscrit",
    ).encode("utf-8")

    def application(environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        if environ.get("PATH_INFO") not in {"/", "/dashboard"}:
            return readiness_app(environ, start_response)
        if environ.get("REQUEST_METHOD") != "GET":
            body = b"Method Not Allowed"
            start_response("405 Method Not Allowed", [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
            ])
            return [body]
        if environ.get("wsgi.url_scheme") != "https":
            body = b"HTTPS Required"
            start_response("403 Forbidden", [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
            ])
            return [body]
        start_response("200 OK", [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(dashboard_html))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "DENY"),
            ("Referrer-Policy", "no-referrer"),
            ("Content-Security-Policy",
             "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
             "connect-src 'self'; img-src 'self' data:; font-src 'self' data:; "
             "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"),
        ])
        return [dashboard_html]

    return application


class LazyWSGIApplication:
    """Delay secret/config validation until the server receives its first request."""

    def __init__(self):
        self._application: Callable[..., list[bytes]] | None = None

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        if self._application is None:
            self._application = create_app()
        return self._application(environ, start_response)


app = LazyWSGIApplication()
