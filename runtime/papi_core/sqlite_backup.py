"""Sauvegarde cohérente, vérification et restauration sûre des bases SQLite locales."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class BackupRestoreError(ValueError):
    """Sauvegarde ou restauration SQLite refusée."""


_FORMAT_VERSION = 1
_MAX_BACKUP_BYTES = 2 * 1024 * 1024 * 1024


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _integrity(path: Path) -> tuple[str, int]:
    if path.is_symlink() or not path.is_file():
        raise BackupRestoreError("La base SQLite doit être un fichier régulier, sans lien symbolique.")
    try:
        with sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True, timeout=15) as db:
            db.execute("PRAGMA query_only=ON")
            result = [row[0] for row in db.execute("PRAGMA integrity_check")]
            if result != ["ok"]:
                raise BackupRestoreError("Échec de PRAGMA integrity_check.")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            return "ok", int(version)
    except (sqlite3.Error, OSError, TypeError) as exc:
        raise BackupRestoreError("Base SQLite illisible ou corrompue.") from exc


def _write_exclusive(path: Path, content: bytes, mode: int = 0o600) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, mode)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def create_sqlite_backup(database_path: Path, backup_dir: Path) -> dict[str, Any]:
    """Crée un snapshot SQLite cohérent via l'API backup, puis un manifeste SHA-256."""
    source, directory = Path(database_path), Path(backup_dir)
    if source.is_symlink() or not source.is_file():
        raise BackupRestoreError("La base source doit exister et être un fichier régulier.")
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise BackupRestoreError("Répertoire de sauvegarde invalide.")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    _integrity(source)

    fd, temporary_name = tempfile.mkstemp(prefix=".papi-backup-", suffix=".tmp", dir=directory)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with sqlite3.connect(f"file:{source.resolve()}?mode=ro", uri=True, timeout=30) as origin:
            with sqlite3.connect(temporary, timeout=30) as target:
                origin.backup(target, pages=256, sleep=0.01)
                target.execute("PRAGMA integrity_check")
        os.chmod(temporary, 0o600)
        integrity, user_version = _integrity(temporary)
        size = temporary.stat().st_size
        if size <= 0 or size > _MAX_BACKUP_BYTES:
            raise BackupRestoreError("Taille de sauvegarde hors limites.")
        digest = _sha256(temporary)
        backup_path = directory / f"sqlite-{digest}.sqlite3"
        try:
            os.link(temporary, backup_path, follow_symlinks=False)
        except FileExistsError:
            if backup_path.is_symlink() or not backup_path.is_file() or _sha256(backup_path) != digest:
                raise BackupRestoreError("Une sauvegarde homonyme existe avec un contenu différent.")
        os.chmod(backup_path, 0o600)
        manifest = {
            "format_version": _FORMAT_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "backup_file": backup_path.name,
            "size_bytes": size,
            "sha256": digest,
            "integrity_check": integrity,
            "user_version": user_version,
        }
        manifest_path = directory / f"sqlite-{digest}.manifest.json"
        encoded = (json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
        if manifest_path.exists() or manifest_path.is_symlink():
            if manifest_path.is_symlink() or manifest_path.read_bytes() != encoded:
                raise BackupRestoreError("Manifeste existant incohérent.")
        else:
            _write_exclusive(manifest_path, encoded)
        return {"status": "backup_created", "backup_path": str(backup_path),
                "manifest_path": str(manifest_path), "sha256": digest,
                "size_bytes": size, "integrity_check": integrity,
                "user_version": user_version}
    except (OSError, sqlite3.Error) as exc:
        raise BackupRestoreError("Création de la sauvegarde SQLite impossible.") from exc
    finally:
        temporary.unlink(missing_ok=True)


def verify_sqlite_backup(manifest_path: Path) -> dict[str, Any]:
    """Vérifie le manifeste, le digest, la taille et l'intégrité SQLite sans modifier les fichiers."""
    manifest_file = Path(manifest_path)
    if manifest_file.is_symlink() or not manifest_file.is_file():
        raise BackupRestoreError("Manifeste absent ou lien symbolique interdit.")
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or type(manifest.get("format_version")) is not int or manifest["format_version"] != _FORMAT_VERSION:
            raise BackupRestoreError("Version de manifeste invalide.")
        name = manifest.get("backup_file")
        if not isinstance(name, str) or Path(name).name != name or not name.endswith(".sqlite3"):
            raise BackupRestoreError("Nom de sauvegarde invalide.")
        backup = manifest_file.parent / name
        if backup.is_symlink() or not backup.is_file():
            raise BackupRestoreError("Fichier de sauvegarde absent ou lien symbolique interdit.")
        size = backup.stat().st_size
        if size <= 0 or size > _MAX_BACKUP_BYTES or size != manifest.get("size_bytes"):
            raise BackupRestoreError("Taille de sauvegarde incohérente.")
        digest = _sha256(backup)
        if digest != manifest.get("sha256"):
            raise BackupRestoreError("Empreinte SHA-256 de sauvegarde incorrecte.")
        integrity, user_version = _integrity(backup)
        if manifest.get("integrity_check") != "ok" or manifest.get("user_version") != user_version:
            raise BackupRestoreError("Métadonnées d'intégrité incohérentes.")
        return {"status": "verified", "backup_path": str(backup),
                "sha256": digest, "size_bytes": size,
                "integrity_check": integrity, "user_version": user_version}
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, KeyError) as exc:
        if isinstance(exc, BackupRestoreError):
            raise
        raise BackupRestoreError("Manifeste ou sauvegarde illisible.") from exc


def restore_sqlite_backup(manifest_path: Path, destination_path: Path) -> dict[str, Any]:
    """Restaure vers un nouveau chemin seulement ; ne remplace jamais une base existante."""
    verified = verify_sqlite_backup(manifest_path)
    destination = Path(destination_path)
    if destination.is_symlink() or destination.exists():
        raise BackupRestoreError("La destination doit être absente ; aucun écrasement n'est autorisé.")
    if destination.parent.is_symlink() or (destination.parent.exists() and not destination.parent.is_dir()):
        raise BackupRestoreError("Répertoire de destination invalide.")
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary_name = tempfile.mkstemp(prefix=".papi-restore-", suffix=".tmp", dir=destination.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with sqlite3.connect(f"file:{Path(verified['backup_path']).resolve()}?mode=ro", uri=True) as origin:
            with sqlite3.connect(temporary) as target:
                origin.backup(target, pages=256, sleep=0.01)
        os.chmod(temporary, 0o600)
        integrity, user_version = _integrity(temporary)
        if integrity != "ok" or user_version != verified["user_version"]:
            raise BackupRestoreError("La base restaurée ne passe pas les contrôles.")
        os.link(temporary, destination, follow_symlinks=False)
        os.chmod(destination, 0o600)
        return {"status": "restored", "destination_path": str(destination),
                "sha256": _sha256(destination), "integrity_check": integrity,
                "user_version": user_version, "overwrite": False}
    except FileExistsError as exc:
        raise BackupRestoreError("La destination existe déjà ; restauration annulée.") from exc
    except (OSError, sqlite3.Error) as exc:
        raise BackupRestoreError("Restauration SQLite annulée.") from exc
    finally:
        temporary.unlink(missing_ok=True)
