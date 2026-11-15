"""Prévisualisation inter-instances paginée, bornée et strictement sans écriture."""
from __future__ import annotations

from typing import Any, Callable

from .principal import require_authenticated_agent_principal
from .reconciliation import build_reconciliation_preview
from .sync_readiness import build_sync_readiness_report


class CollaborationSyncError(ValueError):
    """Snapshot distant incomplet, mal formé ou non borné."""


def _collect_pages(
    fetch_page: Callable[..., dict[str, Any]],
    *,
    principal: object,
    page_size: int,
    max_pages: int,
    id_field: str,
    kind: str,
) -> list[dict[str, Any]]:
    cursor: str | None = None
    seen_cursors: set[str] = set()
    seen_ids: set[str] = set()
    records: list[dict[str, Any]] = []

    for _page_number in range(max_pages):
        response = fetch_page(principal=principal, limit=page_size, cursor=cursor)
        if not isinstance(response, dict) or set(response) != {"items", "next_cursor"}:
            raise CollaborationSyncError(f"Page distante {kind} mal formée.")
        items, next_cursor = response["items"], response["next_cursor"]
        if not isinstance(items, list) or len(items) > page_size:
            raise CollaborationSyncError(f"Nombre d'éléments invalide dans la page {kind}.")
        if next_cursor is not None and (
            not isinstance(next_cursor, str) or not next_cursor or len(next_cursor) > 512
        ):
            raise CollaborationSyncError(f"Curseur distant {kind} invalide.")
        for row in items:
            if not isinstance(row, dict):
                raise CollaborationSyncError(f"Enregistrement distant {kind} invalide.")
            record_id = row.get(id_field)
            if not isinstance(record_id, str) or not record_id:
                raise CollaborationSyncError(f"Identifiant distant {kind} absent.")
            if record_id in seen_ids:
                raise CollaborationSyncError(f"Identifiant distant {kind} répété entre les pages.")
            seen_ids.add(record_id)
            records.append(row)
        if next_cursor is None:
            return records
        if next_cursor in seen_cursors or next_cursor == cursor:
            raise CollaborationSyncError(f"Boucle de pagination distante {kind} détectée.")
        seen_cursors.add(next_cursor)
        cursor = next_cursor

    raise CollaborationSyncError(
        f"Limite de {max_pages} pages atteinte pour {kind}; snapshot incomplet refusé."
    )


def build_live_collaboration_preview(
    *,
    principal: object,
    local_memory: list[dict[str, Any]],
    local_messages: list[dict[str, Any]],
    remote_store: Any,
    page_size: int = 100,
    max_pages: int = 100,
) -> dict[str, Any]:
    """Lit les snapshots distants et construit un aperçu sans écriture."""
    require_authenticated_agent_principal(principal)
    if remote_store is None:
        raise CollaborationSyncError("Un adaptateur distant explicite est obligatoire.")
    memory_fetch = getattr(remote_store, "search_memory", None)
    message_fetch = getattr(remote_store, "read_messages", None)
    if not callable(memory_fetch) or not callable(message_fetch):
        raise CollaborationSyncError("L'adaptateur distant ne fournit pas les lectures attendues.")
    if isinstance(page_size, bool) or not isinstance(page_size, int) or not 1 <= page_size <= 100:
        raise CollaborationSyncError("page_size doit être compris entre 1 et 100.")
    if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= 100:
        raise CollaborationSyncError("max_pages doit être compris entre 1 et 100.")

    remote_memory = _collect_pages(
        memory_fetch, principal=principal, page_size=page_size, max_pages=max_pages,
        id_field="memory_id", kind="mémoire",
    )
    remote_messages = _collect_pages(
        message_fetch, principal=principal, page_size=page_size, max_pages=max_pages,
        id_field="message_id", kind="messagerie",
    )
    preview = build_reconciliation_preview(
        principal=principal,
        local_memory=local_memory,
        remote_memory=remote_memory,
        local_messages=local_messages,
        remote_messages=remote_messages,
    )
    readiness = build_sync_readiness_report(preview)
    return {
        "preview": preview,
        "readiness": readiness,
        "remote_snapshot": {
            "memory_records": len(remote_memory),
            "message_records": len(remote_messages),
            "complete": True,
            "pages_bounded": True,
        },
        "writes_performed": False,
        "sync_enabled": False,
    }
