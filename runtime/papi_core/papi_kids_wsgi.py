"""Production WSGI composition for the authenticated PAPI KIDS API."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from .papi_kids_editorial_approval import (
    build_pkp0001_editorial_preview_reader,
    build_postgres_editorial_approval_handler,
)
from .papi_kids_manuscript_api import create_papi_kids_manuscript_app
from .papi_kids_postgres_queue import (
    build_postgres_asset_reviewer,
    build_postgres_library_reader,
    build_postgres_queue_registrar,
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
    preview_reader = build_pkp0001_editorial_preview_reader(
        root, project_root=Path(__file__).resolve().parents[2],
    )
    approval_handler = build_postgres_editorial_approval_handler(
        factory, preview_reader=preview_reader, storage_root=root,
        reviewer_id=os.environ.get("PAPI_KIDS_REVIEWER_ID", ""),
    )
    return create_papi_kids_manuscript_app(
        storage_root=root,
        queue_registrar=build_postgres_queue_registrar(factory),
        status_reader=build_postgres_status_reader(factory),
        review_handler=build_postgres_asset_reviewer(factory),
        library_reader=build_postgres_library_reader(factory),
        editorial_preview_reader=preview_reader,
        editorial_approval_handler=approval_handler,
    )


class LazyWSGIApplication:
    """Delay secret/config validation until the server receives its first request."""

    def __init__(self):
        self._application: Callable[..., list[bytes]] | None = None

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        if self._application is None:
            self._application = create_app()
        return self._application(environ, start_response)


app = LazyWSGIApplication()
