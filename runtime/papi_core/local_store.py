"""Journal SQLite local append-only pour les écritures mémoire et PAPI CHAT."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


class LocalStoreError(ValueError):
    """Magasin local indisponible, corrompu ou incohérent."""


_SCHEMA = """
CREATE TABLE IF NOT EXISTS local_journal_records (
    kind TEXT NOT NULL CHECK(kind IN ('memory', 'message')),
    record_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    record_json TEXT NOT NULL,
    PRIMARY KEY(kind, record_id),
    UNIQUE(kind, event_id)
);
CREATE TRIGGER IF NOT EXISTS local_journal_no_update
BEFORE UPDATE ON local_journal_records
BEGIN SELECT RAISE(ABORT, 'append-only journal'); END;
CREATE TRIGGER IF NOT EXISTS local_journal_no_delete
BEFORE DELETE ON local_journal_records
BEGIN SELECT RAISE(ABORT, 'append-only journal'); END;
"""


def _database(path: Path) -> Path:
    target = Path(path)
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise LocalStoreError("La base locale doit être un fichier SQLite réel, sans lien symbolique.")
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not target.exists():
        descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
    os.chmod(target, 0o600)
    return target


def append_local_record(database: Path, *, kind: str, record_id: str,
                        event_id: str, created_at: str,
                        record: dict[str, Any]) -> None:
    if kind not in {"memory", "message"} or not all(
        isinstance(value, str) and value.strip()
        for value in (record_id, event_id, created_at)
    ) or not isinstance(record, dict):
        raise LocalStoreError("Identité ou type d'enregistrement invalide.")
    try:
        payload = json.dumps(record, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False)
        path = _database(database)
        with sqlite3.connect(path, timeout=30, isolation_level=None) as db:
            db.execute("PRAGMA busy_timeout=30000")
            db.executescript(_SCHEMA)
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "INSERT INTO local_journal_records "
                "(kind,record_id,event_id,created_at,record_json) VALUES (?,?,?,?,?)",
                (kind, record_id, event_id, created_at, payload),
            )
            db.commit()
    except (OSError, sqlite3.Error, TypeError, ValueError) as exc:
        raise LocalStoreError("Écriture atomique du journal SQLite refusée.") from exc


def load_local_records(database: Path | None, kind: str) -> list[dict[str, Any]]:
    if database is None:
        return []
    path = Path(database)
    if not path.exists():
        return []
    if path.is_symlink() or not path.is_file() or kind not in {"memory", "message"}:
        raise LocalStoreError("Base ou type de journal local invalide.")
    try:
        with sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True, timeout=10) as db:
            db.execute("PRAGMA query_only=ON")
            tables = {row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            if "local_journal_records" not in tables:
                return []
            rows = db.execute(
                "SELECT record_json FROM local_journal_records WHERE kind=? ORDER BY rowid",
                (kind,),
            ).fetchall()
        records = []
        for (payload,) in rows:
            record = json.loads(payload)
            if not isinstance(record, dict):
                raise LocalStoreError("Enregistrement SQLite non objet.")
            records.append(record)
        return records
    except (OSError, sqlite3.Error, json.JSONDecodeError, TypeError) as exc:
        raise LocalStoreError("Lecture du journal SQLite impossible.") from exc
