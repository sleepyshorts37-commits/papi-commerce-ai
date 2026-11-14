"""Transactional lifecycle ledger for PAPI agent identities.

This local ledger serializes identity metadata transitions. It does not create
keys, deploy agents, grant external access, or perform business actions.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any

_ALLOWED_OPERATIONS = {"provision", "rotate", "permissions", "revoke"}
_ALLOWED_STATUSES = {"active", "revoked"}


class IdentityTransactionError(ValueError):
    """A lifecycle transaction is invalid, conflicting, or unverifiable."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise IdentityTransactionError("Données de transaction non sérialisables.") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


class IdentityTransactionManager:
    """SQLite-backed, idempotent and hash-chained identity state transitions."""

    def __init__(self, database: Path):
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.database.is_symlink():
            raise IdentityTransactionError("Base identité symbolique interdite.")
        self._initialize()
        os.chmod(self.database, 0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS identity_state (
                    agent_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL CHECK(status IN ('active','revoked')),
                    revision INTEGER NOT NULL CHECK(revision >= 1),
                    key_version INTEGER NOT NULL CHECK(key_version >= 1),
                    permissions_json TEXT NOT NULL,
                    prohibited_json TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS identity_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id TEXT NOT NULL UNIQUE,
                    agent_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_digest TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE,
                    event_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    UNIQUE(agent_id, idempotency_key)
                )
            """)
            db.execute("""
                CREATE TRIGGER IF NOT EXISTS identity_events_no_update
                BEFORE UPDATE ON identity_events BEGIN
                    SELECT RAISE(ABORT, 'identity event log is append-only');
                END
            """)
            db.execute("""
                CREATE TRIGGER IF NOT EXISTS identity_events_no_delete
                BEFORE DELETE ON identity_events BEGIN
                    SELECT RAISE(ABORT, 'identity event log is append-only');
                END
            """)

    @staticmethod
    def _validate_id(value: str, label: str) -> None:
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        if not isinstance(value, str) or not value or any(c not in allowed for c in value):
            raise IdentityTransactionError(f"{label} invalide.")

    @staticmethod
    def _permission_list(value: Any, label: str) -> list[str]:
        if not isinstance(value, (list, tuple, set)):
            raise IdentityTransactionError(f"Liste {label} invalide.")
        items = list(value)
        if any(not isinstance(item, str) or not item or len(item) > 128 for item in items):
            raise IdentityTransactionError(f"Permission {label} invalide.")
        if len(items) != len(set(items)):
            raise IdentityTransactionError(f"Permission {label} dupliquée.")
        return sorted(items)

    def apply(
        self, *, agent_id: str, operation: str, idempotency_key: str,
        actor_id: str, expected_revision: int | None = None,
        key_version: int | None = None, permissions: list[str] | None = None,
        prohibited: list[str] | None = None, approval_ref: str | None = None,
    ) -> dict[str, Any]:
        self._validate_id(agent_id, "Identifiant agent")
        self._validate_id(actor_id, "Identifiant acteur")
        self._validate_id(idempotency_key, "Clé d'idempotence")
        if operation not in _ALLOWED_OPERATIONS:
            raise IdentityTransactionError("Opération de cycle de vie inconnue.")
        if not isinstance(approval_ref, str) or not approval_ref.strip():
            raise IdentityTransactionError("Approbation humaine explicite requise pour toute transition.")

        perms = self._permission_list(permissions or [], "autorisée")
        denied = self._permission_list(prohibited or [], "interdite")
        if set(perms) & set(denied):
            raise IdentityTransactionError("Une permission ne peut être autorisée et interdite.")
        request = {
            "agent_id": agent_id, "operation": operation,
            "idempotency_key": idempotency_key, "actor_id": actor_id,
            "expected_revision": expected_revision, "key_version": key_version,
            "permissions": perms, "prohibited": denied, "approval_ref": approval_ref,
        }
        request_digest = _digest(request)
        now = int(time.time())

        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                prior = db.execute(
                    "SELECT request_digest,event_json FROM identity_events "
                    "WHERE agent_id=? AND idempotency_key=?",
                    (agent_id, idempotency_key),
                ).fetchone()
                if prior:
                    if prior["request_digest"] != request_digest:
                        raise IdentityTransactionError("Clé d'idempotence réutilisée avec une autre requête.")
                    result = json.loads(prior["event_json"])
                    db.execute("COMMIT")
                    return {**result, "idempotent_replay": True}

                current = db.execute(
                    "SELECT * FROM identity_state WHERE agent_id=?", (agent_id,)
                ).fetchone()
                if current is None:
                    if operation != "provision":
                        raise IdentityTransactionError("Identité absente : provision obligatoire.")
                    if expected_revision not in (None, 0):
                        raise IdentityTransactionError("Révision initiale attendue invalide.")
                    if type(key_version) is not int or key_version != 1:
                        raise IdentityTransactionError("La provision exige la version de clé 1.")
                    status, revision = "active", 1
                    next_permissions, next_prohibited = perms, denied
                else:
                    if expected_revision != current["revision"]:
                        raise IdentityTransactionError("Conflit de révision : relecture requise.")
                    if current["status"] == "revoked":
                        raise IdentityTransactionError("Identité révoquée : transition interdite.")
                    status = current["status"]
                    revision = current["revision"] + 1
                    current_permissions = json.loads(current["permissions_json"])
                    current_prohibited = json.loads(current["prohibited_json"])
                    if operation == "provision":
                        raise IdentityTransactionError("Identité déjà provisionnée.")
                    if operation == "rotate":
                        if type(key_version) is not int or key_version != current["key_version"] + 1:
                            raise IdentityTransactionError("La rotation doit incrémenter exactement la version.")
                        if permissions is not None or prohibited is not None:
                            raise IdentityTransactionError("La rotation ne modifie pas les permissions.")
                        next_permissions, next_prohibited = current_permissions, current_prohibited
                    elif operation == "permissions":
                        if key_version is not None:
                            raise IdentityTransactionError("Une mise à jour des permissions ne change pas la clé.")
                        if permissions is None:
                            raise IdentityTransactionError("Nouvel ensemble de permissions obligatoire.")
                        next_permissions = perms
                        next_prohibited = denied if prohibited is not None else current_prohibited
                        if set(next_permissions) & set(next_prohibited):
                            raise IdentityTransactionError("Permission interdite dans le nouvel ensemble.")
                    else:  # revoke
                        if key_version is not None or permissions is not None or prohibited is not None:
                            raise IdentityTransactionError("La révocation ne modifie ni clé ni permissions.")
                        status = "revoked"
                        next_permissions, next_prohibited = [], current_prohibited

                resulting_key_version = key_version if operation in {"provision", "rotate"} else (
                    current["key_version"] if current else 1
                )
                previous = db.execute(
                    "SELECT event_hash FROM identity_events ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
                previous_hash = previous["event_hash"] if previous else "0" * 64
                event = {
                    "agent_id": agent_id, "operation": operation, "actor_id": actor_id,
                    "status": status, "revision": revision,
                    "key_version": resulting_key_version,
                    "permissions": next_permissions, "prohibited": next_prohibited,
                    "approval_ref": approval_ref, "request_digest": request_digest,
                    "previous_hash": previous_hash, "created_at": now,
                }
                event_hash = hashlib.sha256(bytes.fromhex(previous_hash) + _canonical(event)).hexdigest()
                transaction_id = hashlib.sha256(
                    (agent_id + ":" + idempotency_key + ":" + request_digest).encode()
                ).hexdigest()
                event_record = {**event, "transaction_id": transaction_id, "event_hash": event_hash}
                db.execute(
                    """INSERT INTO identity_events
                    (transaction_id,agent_id,operation,idempotency_key,request_digest,
                     previous_hash,event_hash,event_json,created_at)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (transaction_id, agent_id, operation, idempotency_key, request_digest,
                     previous_hash, event_hash, json.dumps(event_record, sort_keys=True), now),
                )
                db.execute(
                    """INSERT INTO identity_state
                    (agent_id,status,revision,key_version,permissions_json,prohibited_json,updated_at)
                    VALUES (?,?,?,?,?,?,?)
                    ON CONFLICT(agent_id) DO UPDATE SET
                    status=excluded.status, revision=excluded.revision,
                    key_version=excluded.key_version, permissions_json=excluded.permissions_json,
                    prohibited_json=excluded.prohibited_json, updated_at=excluded.updated_at""",
                    (agent_id, status, revision, resulting_key_version,
                     json.dumps(next_permissions), json.dumps(next_prohibited), now),
                )
                db.execute("COMMIT")
                return {**event_record, "idempotent_replay": False}
            except Exception:
                db.execute("ROLLBACK")
                raise

    def get_state(self, agent_id: str) -> dict[str, Any] | None:
        self._validate_id(agent_id, "Identifiant agent")
        with closing(self._connect()) as db:
            row = db.execute("SELECT * FROM identity_state WHERE agent_id=?", (agent_id,)).fetchone()
        if row is None:
            return None
        return {
            "agent_id": row["agent_id"], "status": row["status"],
            "revision": row["revision"], "key_version": row["key_version"],
            "permissions": json.loads(row["permissions_json"]),
            "prohibited": json.loads(row["prohibited_json"]),
            "updated_at": row["updated_at"],
        }

    def verify_event_chain(self) -> dict[str, Any]:
        with closing(self._connect()) as db:
            rows = db.execute("SELECT * FROM identity_events ORDER BY sequence").fetchall()
        previous_hash = "0" * 64
        for row in rows:
            event = json.loads(row["event_json"])
            if row["previous_hash"] != previous_hash or event.get("previous_hash") != previous_hash:
                raise IdentityTransactionError("Rupture de chaîne d'audit détectée.")
            expected = hashlib.sha256(bytes.fromhex(previous_hash) + _canonical({
                key: value for key, value in event.items()
                if key not in {"transaction_id", "event_hash"}
            })).hexdigest()
            if expected != row["event_hash"] or event.get("event_hash") != row["event_hash"]:
                raise IdentityTransactionError("Empreinte d'événement invalide.")
            previous_hash = row["event_hash"]
        return {"valid": True, "events": len(rows), "head_hash": previous_hash}
