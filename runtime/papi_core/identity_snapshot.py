"""Read-only extraction of canonical agent registry and SQLite identity ledger snapshots."""
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
_REQUIRED_TABLES = {"identity_state"}
_REQUIRED_COLUMNS = {
    "agent_id", "status", "revision", "key_version",
    "permissions_json", "prohibited_json",
}


def _regular_file(path: Path, label: str) -> Path:
    candidate = Path(path)
    try:
        info = candidate.lstat()
    except OSError as exc:
        raise IdentitySnapshotError(f"Source {label} inaccessible.") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise IdentitySnapshotError(f"Source {label} doit être un fichier régulier non symbolique.")
    return candidate.resolve(strict=True)


def load_registry_snapshot(path: Path) -> list[dict[str, Any]]:
    """Load data/agents.json without following symlinks or accepting malformed roots."""
    source = _regular_file(Path(path), "registre JSON")
    try:
        if source.stat().st_size > _MAX_REGISTRY_BYTES:
            raise IdentitySnapshotError("Registre JSON trop volumineux.")
        raw = source.read_text(encoding="utf-8", errors="strict")
        document = json.loads(raw)
    except IdentitySnapshotError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IdentitySnapshotError("Registre JSON illisible ou invalide.") from exc
    if not isinstance(document, dict) or not isinstance(document.get("agents"), list):
        raise IdentitySnapshotError("Schéma du registre JSON invalide : agents doit être une liste.")
    if any(not isinstance(agent, dict) for agent in document["agents"]):
        raise IdentitySnapshotError("Le registre contient une entrée agent invalide.")
    return document["agents"]


def load_ledger_snapshot(path: Path) -> list[dict[str, Any]]:
    """Read identity_state using SQLite URI mode=ro; never initializes or mutates a DB."""
    source = _regular_file(Path(path), "ledger SQLite")
    uri = source.as_uri() + "?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
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
        finally:
            connection.close()
    except IdentitySnapshotError:
        raise
    except sqlite3.Error as exc:
        raise IdentitySnapshotError("Ledger SQLite illisible ou invalide.") from exc

    result: list[dict[str, Any]] = []
    for row in rows:
        try:
            permissions = json.loads(row["permissions_json"])
            prohibited = json.loads(row["prohibited_json"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise IdentitySnapshotError("Permissions JSON invalides dans le ledger.") from exc
        if not isinstance(permissions, list) or not isinstance(prohibited, list):
            raise IdentitySnapshotError("Permissions et interdictions doivent être des listes.")
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
