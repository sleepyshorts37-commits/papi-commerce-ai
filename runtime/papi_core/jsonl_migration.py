"""Migration contrôlée, sauvegardée et idempotente des journaux JSONL."""
from __future__ import annotations
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from .chat import ChatError, validate_message
from .local_store import LocalStoreError, _SCHEMA, _database
from .memory import MemoryError, _read_events


class MigrationError(ValueError):
    """Migration JSONL refusée ou incohérente."""


_MAX_SOURCE_BYTES = 50 * 1024 * 1024


def _read_source(path: Path, kind: str, agents_path: Path) -> tuple[bytes, list[dict[str, Any]]]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise MigrationError("Le journal source doit être un fichier régulier, sans lien symbolique.")
    raw = source.read_bytes()
    if len(raw) > _MAX_SOURCE_BYTES:
        raise MigrationError("Journal source supérieur à la limite de 50 Mio.")
    if kind == "memory":
        try:
            records = _read_events(source)
        except (MemoryError, OSError, UnicodeError) as exc:
            raise MigrationError(f"Journal mémoire invalide : {exc}") from exc
    elif kind == "message":
        records, seen = [], set()
        try:
            lines = raw.decode("utf-8").splitlines()
        except UnicodeDecodeError as exc:
            raise MigrationError("Journal PAPI CHAT non UTF-8.") from exc
        for number, line in enumerate(lines, 1):
            if not line.strip():
                raise MigrationError(f"Ligne vide interdite dans PAPI CHAT ({number}).")
            try:
                message = json.loads(line)
                validate_message(message, agents_path)
            except (json.JSONDecodeError, ChatError, TypeError) as exc:
                raise MigrationError(f"Message invalide ligne {number}: {exc}") from exc
            message_id = message["message_id"]
            if message_id in seen:
                raise MigrationError(f"Identifiant de message dupliqué ligne {number}.")
            seen.add(message_id)
            records.append(message)
    else:
        raise MigrationError("Type de journal non pris en charge.")
    return raw, records


def _create_verified_backup(source: Path, raw: bytes, digest: str, backup_dir: Path) -> Path:
    directory = Path(backup_dir)
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise MigrationError("Répertoire de sauvegarde invalide.")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = directory / f"{source.name}.{digest}.bak"
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if target.is_symlink() or not target.is_file() or target.read_bytes() != raw:
            raise MigrationError("Une sauvegarde portant ce nom existe mais son contenu diffère.")
        return target
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        target.unlink(missing_ok=True)
        raise
    if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        target.unlink(missing_ok=True)
        raise MigrationError("La vérification SHA-256 de la sauvegarde a échoué.")
    return target


def migrate_jsonl_to_sqlite(*, kind: str, source_path: Path, database_path: Path,
                            backup_dir: Path, agents_path: Path) -> dict[str, Any]:
    """Sauvegarde et migre atomiquement un journal sans modifier ni supprimer la source."""
    try:
        source = Path(source_path)
        raw, records = _read_source(source, kind, Path(agents_path))
        digest = hashlib.sha256(raw).hexdigest()
        backup = _create_verified_backup(source, raw, digest, Path(backup_dir))
        database = _database(Path(database_path))
        with sqlite3.connect(database, timeout=30, isolation_level=None) as db:
            db.execute("PRAGMA busy_timeout=30000")
            db.executescript(_SCHEMA)
            db.execute("""CREATE TABLE IF NOT EXISTS jsonl_migration_runs (
                migration_id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL CHECK(kind IN ('memory','message')),
                source_path TEXT NOT NULL, source_sha256 TEXT NOT NULL,
                backup_path TEXT NOT NULL, record_count INTEGER NOT NULL,
                migrated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(kind, source_path, source_sha256))""")
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute(
                "SELECT record_count, backup_path FROM jsonl_migration_runs "
                "WHERE kind=? AND source_path=? AND source_sha256=?",
                (kind, str(source.resolve()), digest)).fetchone()
            if prior:
                db.rollback()
                return {"status":"already_migrated","kind":kind,"source_sha256":digest,
                        "record_count":prior[0],"backup_path":prior[1],"source_preserved":True}
            for record in records:
                if kind == "memory":
                    record_id = record.get("memory_id") if record.get("event_type") == "remember" else record.get("event_id")
                    event_id, created_at = record.get("event_id"), record.get("created_at")
                else:
                    record_id = event_id = record.get("message_id")
                    created_at = record.get("sent_at")
                if not all(isinstance(v, str) and v.strip() for v in (record_id,event_id,created_at)):
                    raise MigrationError("Identifiants incomplets dans le journal source.")
                payload = json.dumps(record, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False)
                db.execute("INSERT INTO local_journal_records "
                           "(kind,record_id,event_id,created_at,record_json) VALUES (?,?,?,?,?)",
                           (kind,record_id,event_id,created_at,payload))
            db.execute("INSERT INTO jsonl_migration_runs "
                       "(kind,source_path,source_sha256,backup_path,record_count) VALUES (?,?,?,?,?)",
                       (kind,str(source.resolve()),digest,str(backup),len(records)))
            db.commit()
        return {"status":"migrated","kind":kind,"source_sha256":digest,
                "backup_path":str(backup),"record_count":len(records),
                "source_preserved":True,"database_path":str(database)}
    except MigrationError:
        raise
    except (OSError, sqlite3.Error, LocalStoreError, TypeError, ValueError) as exc:
        raise MigrationError(f"Migration annulée : {exc}") from exc
