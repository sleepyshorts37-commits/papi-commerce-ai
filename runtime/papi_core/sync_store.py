"""Lecture en lecture seule des contenus validés dans le magasin d'import SQLite."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import quote


class SyncStoreError(ValueError):
    """Magasin d'import indisponible, incomplet ou incohérent."""


def load_imported_records(database: Path | None, kind: str) -> list[dict[str, Any]]:
    """Charge uniquement les lignes liées à un lot commité, sans jamais écrire."""
    if database is None:
        return []
    path = Path(database)
    if not path.exists():
        return []
    if path.is_symlink() or not path.is_file():
        raise SyncStoreError("Le magasin d'import doit être un fichier SQLite local réel.")
    uri = "file:" + quote(str(path.resolve()), safe="/:") + "?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True, timeout=10) as db:
            db.execute("PRAGMA query_only=ON")
            tables = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            required = {"sync_imported_records", "sync_import_batches", "sync_bundle_receipts", "sync_bundle_receipt_items"}
            if not required.issubset(tables):
                raise SyncStoreError("Schéma du magasin d'import incomplet.")
            rows = db.execute(
                "SELECT r.event_id,r.kind,r.record_id,r.content_digest,r.record_json "
                "FROM sync_imported_records AS r "
                "JOIN sync_import_batches AS b ON b.bundle_digest=r.bundle_digest "
                "JOIN sync_bundle_receipts AS receipt "
                "ON receipt.bundle_digest=b.bundle_digest "
                "AND receipt.status='verified_pending_manual_import' "
                "JOIN sync_bundle_receipt_items AS item "
                "ON item.bundle_digest=receipt.bundle_digest "
                "AND item.event_id=r.event_id AND item.kind=r.kind "
                "AND item.record_id=r.record_id AND item.content_digest=r.content_digest "
                "WHERE r.kind=? ORDER BY b.imported_at,r.rowid",
                (kind,),
            ).fetchall()
            total = db.execute(
                "SELECT COUNT(*) FROM sync_imported_records WHERE kind=?", (kind,)
            ).fetchone()[0]
            if total != len(rows):
                raise SyncStoreError("Contenu sans reçu approuvé correspondant; lecture refusée.")
    except SyncStoreError:
        raise
    except sqlite3.Error as exc:
        raise SyncStoreError("Lecture SQLite du magasin d'import impossible.") from exc

    result = []
    seen_events: set[str] = set()
    seen_records: set[str] = set()
    for event_id, row_kind, record_id, content_digest, record_json in rows:
        if event_id in seen_events or record_id in seen_records:
            raise SyncStoreError("Identifiant importé dupliqué dans le magasin.")
        seen_events.add(event_id)
        seen_records.add(record_id)
        try:
            record = json.loads(record_json)
            canonical = json.dumps(record, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":"), allow_nan=False).encode("utf-8")
        except (TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SyncStoreError("Enregistrement importé illisible.") from exc
        if not isinstance(record, dict) or hashlib.sha256(canonical).hexdigest() != content_digest:
            raise SyncStoreError("Empreinte du contenu importé invalide.")
        if row_kind != kind:
            raise SyncStoreError("Type d'enregistrement importé incohérent.")
        result.append(record)
        if len(result) > 50000:
            raise SyncStoreError("Trop d'enregistrements importés pour une lecture.")
    return result
