"""Hardened, read-only extraction of canonical identity snapshots."""
from __future__ import annotations

import json
import os
import sqlite3
import stat
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .identity_reconciliation import reconcile_identity_snapshots


class IdentitySnapshotError(ValueError):
    """A source cannot be safely or unambiguously snapshotted."""


_MAX_REGISTRY_BYTES = 5 * 1024 * 1024
_MAX_JSON_VALUE_BYTES = 1024 * 1024
_REQUIRED_TABLES = {"identity_state"}
_REQUIRED_COLUMNS = {
    "agent_id", "status", "revision", "key_version",
    "permissions_json", "prohibited_json",
}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise IdentitySnapshotError("Clé JSON dupliquée.")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise IdentitySnapshotError("Valeur numérique JSON non finie interdite.")


def _open_regular_file(path: Path, label: str) -> int:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(os.fspath(path), flags)
        info = os.fstat(descriptor)
    except OSError as exc:
        raise IdentitySnapshotError(f"Source {label} inaccessible ou symbolique.") from exc
    if not stat.S_ISREG(info.st_mode):
        os.close(descriptor)
        raise IdentitySnapshotError(f"Source {label} doit être un fichier régulier.")
    return descriptor


def _read_bounded(descriptor: int, limit: int, label: str) -> bytes:
    before = os.fstat(descriptor)
    if before.st_size > limit:
        raise IdentitySnapshotError(f"Source {label} trop volumineuse.")
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = os.read(descriptor, min(65536, limit + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > limit:
            raise IdentitySnapshotError(f"Source {label} trop volumineuse.")
    after = os.fstat(descriptor)
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
    ) or total != after.st_size:
        raise IdentitySnapshotError(f"Source {label} modifiée pendant la lecture.")
    return b"".join(chunks)


def _load_json_bytes(raw: bytes, label: str) -> Any:
    try:
        text = raw.decode("utf-8", errors="strict")
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
    except IdentitySnapshotError:
        raise
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise IdentitySnapshotError(f"Source {label} illisible ou JSON invalide.") from exc


def load_registry_snapshot(path: Path) -> list[dict[str, Any]]:
    """Read the canonical registry through a no-follow descriptor with a strict size cap."""
    descriptor = _open_regular_file(Path(path), "registre JSON")
    try:
        document = _load_json_bytes(_read_bounded(descriptor, _MAX_REGISTRY_BYTES, "registre JSON"), "registre JSON")
    finally:
        os.close(descriptor)
    if not isinstance(document, dict) or not isinstance(document.get("agents"), list):
        raise IdentitySnapshotError("Schéma du registre JSON invalide : agents doit être une liste.")
    if any(not isinstance(agent, dict) for agent in document["agents"]):
        raise IdentitySnapshotError("Le registre contient une entrée agent invalide.")
    return document["agents"]


def _sqlite_descriptor_uri(descriptor: int) -> str:
    """Return a URI pinned to an already-open descriptor; fail closed without procfs."""
    proc_path = Path(f"/proc/self/fd/{descriptor}")
    if not proc_path.exists():
        raise IdentitySnapshotError("Lecture SQLite sécurisée indisponible : /proc/self/fd absent.")
    return proc_path.as_uri() + "?mode=ro"


def load_ledger_snapshot(path: Path) -> list[dict[str, Any]]:
    """Read SQLite via a pinned no-follow descriptor and URI mode=ro; never create a DB."""
    descriptor = _open_regular_file(Path(path), "ledger SQLite")
    connection: sqlite3.Connection | None = None
    try:
        uri = _sqlite_descriptor_uri(descriptor)
        connection = sqlite3.connect(uri, uri=True, timeout=5)
        connection.row_factory = sqlite3.Row
        tables = {
            row["name"] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if not _REQUIRED_TABLES.issubset(tables):
            raise IdentitySnapshotError("Table identity_state absente du ledger.")
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(identity_state)")
        }
        if not _REQUIRED_COLUMNS.issubset(columns):
            raise IdentitySnapshotError("Schéma identity_state incomplet.")
        rows = connection.execute(
            """SELECT agent_id,status,revision,key_version,permissions_json,prohibited_json
               FROM identity_state ORDER BY agent_id"""
        ).fetchall()
    except IdentitySnapshotError:
        raise
    except (sqlite3.Error, OSError, ValueError) as exc:
        raise IdentitySnapshotError("Ledger SQLite illisible ou invalide.") from exc
    finally:
        if connection is not None:
            connection.close()
        os.close(descriptor)

    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row["agent_id"], str) or not row["agent_id"].strip():
            raise IdentitySnapshotError("Identifiant agent invalide dans le ledger.")
        if not isinstance(row["status"], str) or not row["status"]:
            raise IdentitySnapshotError("Statut invalide dans le ledger.")
        if type(row["revision"]) is not int or row["revision"] < 1:
            raise IdentitySnapshotError("Révision invalide dans le ledger.")
        if type(row["key_version"]) is not int or row["key_version"] < 1:
            raise IdentitySnapshotError("Version de clé invalide dans le ledger.")
        permissions = _load_json_bytes(row["permissions_json"].encode("utf-8"), "permissions ledger")
        prohibited = _load_json_bytes(row["prohibited_json"].encode("utf-8"), "interdictions ledger")
        if not isinstance(permissions, list) or not isinstance(prohibited, list):
            raise IdentitySnapshotError("Permissions et interdictions doivent être des listes.")
        if len(row["permissions_json"].encode("utf-8")) > _MAX_JSON_VALUE_BYTES or len(row["prohibited_json"].encode("utf-8")) > _MAX_JSON_VALUE_BYTES:
            raise IdentitySnapshotError("Valeur JSON du ledger trop volumineuse.")
        result.append({
            "agent_id": row["agent_id"], "status": row["status"],
            "revision": row["revision"], "key_version": row["key_version"],
            "permissions": permissions, "prohibited": prohibited,
        })
    return result


def reconcile_identity_sources(registry_path: Path, ledger_path: Path) -> dict[str, Any]:
    """Extract both local sources read-only, then invoke the Mission 66 reconciler."""
    registry = load_registry_snapshot(registry_path)
    ledger = load_ledger_snapshot(ledger_path)
    return reconcile_identity_snapshots(registry, ledger)
