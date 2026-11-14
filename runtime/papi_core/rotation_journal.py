"""Crash-recovery journal for local Ed25519 private-key rotation.

The journal temporarily contains the previous private key and is therefore
created with mode 0600 inside a private directory. It is never logged.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import stat
from pathlib import Path
from typing import Any


class RotationJournalError(ValueError):
    """A pending key rotation cannot be safely recovered."""


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_name("." + path.name + "." + secrets.token_hex(12) + ".tmp")
    fd = None
    exists = False
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        exists = True
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as handle:
            fd = None
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        exists = False
        _fsync_directory(path.parent)
    finally:
        if fd is not None:
            os.close(fd)
        if exists:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass


def _journal_path(private_path: Path) -> Path:
    return private_path.with_name(private_path.name + ".rotation-journal")


def _read_secure_journal(path: Path) -> dict[str, Any]:
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise RotationJournalError("Journal de rotation non régulier : accès fermé.")
        if stat.S_IMODE(metadata.st_mode) & 0o077:
            raise RotationJournalError("Permissions du journal de rotation trop ouvertes.")
        if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
            raise RotationJournalError("Propriétaire du journal de rotation incorrect.")
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RotationJournalError("Journal de rotation absent ou illisible : accès fermé.") from exc
    required = {
        "schema_version", "transaction_id", "private_path_name",
        "old_private_b64", "new_private_b64", "old_registry_b64",
        "new_registry_b64", "old_private_sha256", "new_private_sha256",
        "old_registry_sha256", "new_registry_sha256",
    }
    if not isinstance(data, dict) or set(data) != required or data.get("schema_version") != 1:
        raise RotationJournalError("Structure du journal de rotation invalide.")
    if data.get("private_path_name") != path.name.removesuffix(".rotation-journal"):
        raise RotationJournalError("Le journal ne correspond pas au fichier de clé attendu.")
    try:
        decoded = {
            "old_private": base64.b64decode(data["old_private_b64"], validate=True),
            "new_private": base64.b64decode(data["new_private_b64"], validate=True),
            "old_registry": base64.b64decode(data["old_registry_b64"], validate=True),
            "new_registry": base64.b64decode(data["new_registry_b64"], validate=True),
        }
    except (ValueError, TypeError) as exc:
        raise RotationJournalError("Contenu du journal de rotation invalide.") from exc
    for name, content in decoded.items():
        if _digest(content) != data[name + "_sha256"]:
            raise RotationJournalError("Empreinte du journal de rotation incorrecte.")
    return {**data, **decoded}


def _remove_journal(path: Path) -> None:
    path.unlink()
    _fsync_directory(path.parent)


def recover_key_rotation(private_path: Path, registry_path: Path) -> str:
    """Recover a pending two-file rotation; fail closed on ambiguous state."""
    journal = _journal_path(private_path)
    if not journal.exists() and not journal.is_symlink():
        return "clean"
    data = _read_secure_journal(journal)
    try:
        current_private = private_path.read_bytes()
        current_registry = registry_path.read_bytes()
    except OSError as exc:
        raise RotationJournalError("État des fichiers de rotation incomplet : accès fermé.") from exc

    private_hash = _digest(current_private)
    registry_hash = _digest(current_registry)
    old_private = data["old_private_sha256"]
    new_private = data["new_private_sha256"]
    old_registry = data["old_registry_sha256"]
    new_registry = data["new_registry_sha256"]

    if registry_hash == new_registry and private_hash == new_private:
        _remove_journal(journal)
        return "committed"
    if registry_hash == old_registry and private_hash == old_private:
        _remove_journal(journal)
        return "not_started"
    if registry_hash == old_registry and private_hash == new_private:
        _atomic_write(private_path, data["old_private"])
        _remove_journal(journal)
        return "rolled_back"

    # Never guess if a file is modified, missing, or reflects an impossible order.
    raise RotationJournalError(
        "État de rotation ambigu ou modifié ; journal conservé pour récupération manuelle."
    )


def commit_key_rotation(
    private_path: Path,
    registry_path: Path,
    old_private: bytes,
    new_private: bytes,
    old_registry: bytes,
    new_registry: bytes,
) -> None:
    """Durably journal, replace the private key, then atomically publish registry."""
    journal = _journal_path(private_path)
    if journal.exists() or journal.is_symlink():
        raise RotationJournalError("Une rotation précédente doit être récupérée avant de continuer.")
    if private_path.read_bytes() != old_private or registry_path.read_bytes() != old_registry:
        raise RotationJournalError("Les fichiers ont changé depuis la préparation de la rotation.")
    payload = {
        "schema_version": 1,
        "transaction_id": secrets.token_hex(16),
        "private_path_name": private_path.name,
        "old_private_b64": base64.b64encode(old_private).decode("ascii"),
        "new_private_b64": base64.b64encode(new_private).decode("ascii"),
        "old_registry_b64": base64.b64encode(old_registry).decode("ascii"),
        "new_registry_b64": base64.b64encode(new_registry).decode("ascii"),
        "old_private_sha256": _digest(old_private),
        "new_private_sha256": _digest(new_private),
        "old_registry_sha256": _digest(old_registry),
        "new_registry_sha256": _digest(new_registry),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    _atomic_write(journal, encoded)
    try:
        _atomic_write(private_path, new_private)
        _atomic_write(registry_path, new_registry)
        _remove_journal(journal)
    except Exception:
        # Recovery is deterministic: old registry means rollback; new registry
        # means commit. Preserve the journal if the state cannot be proven.
        recover_key_rotation(private_path, registry_path)
        raise
