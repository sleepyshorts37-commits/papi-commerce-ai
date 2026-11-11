"""Authentification cryptographique locale des agents par HMAC-SHA256.

Clés individuelles hors dépôt, signatures liées au contenu, horodatage et anti-rejeu SQLite.
Pour un environnement multi-hôte, préférer une identité de workload ou des signatures asymétriques.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any

DEFAULT_KEY_DIR = Path.home() / ".papi" / "identity" / "keys"
DEFAULT_REPLAY_DB = Path.home() / ".papi" / "identity" / "replay.sqlite3"
MAX_CLOCK_SKEW_SECONDS = 300


class IdentityError(ValueError):
    """Authentification invalide ou configuration d'identité non sûre."""


def _canonical(agent_id: str, timestamp: int, nonce: str, payload: dict[str, Any]) -> bytes:
    if not isinstance(payload, dict):
        raise IdentityError("Le contenu signé doit être un objet.")
    body = {"agent_id": agent_id, "timestamp": timestamp, "nonce": nonce, "payload": payload}
    try:
        return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise IdentityError("Contenu non sérialisable.") from exc


def provision_agent_key(agent_id: str, key_dir: Path = DEFAULT_KEY_DIR) -> Path:
    """Crée une clé individuelle locale. Ne jamais versionner ou transmettre cette clé."""
    if not agent_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in agent_id):
        raise IdentityError("Identifiant d'agent invalide.")
    key_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(key_dir, 0o700)
    except OSError:
        pass
    path = key_dir / f"{agent_id}.key"
    if path.exists():
        raise IdentityError("Une clé existe déjà ; rotation explicite requise.")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(secrets.token_bytes(32))
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


def sign_request(agent_id: str, payload: dict[str, Any], key_path: Path,
                 timestamp: int | None = None, nonce: str | None = None) -> dict[str, Any]:
    """Produit une enveloppe signée ; le secret n'est jamais inclus dans le résultat."""
    if not agent_id:
        raise IdentityError("Identifiant d'agent obligatoire.")
    try:
        key = key_path.read_bytes()
    except OSError as exc:
        raise IdentityError("Clé privée indisponible.") from exc
    if len(key) < 32:
        raise IdentityError("Clé privée trop courte.")
    issued_at = int(time.time()) if timestamp is None else int(timestamp)
    request_nonce = secrets.token_hex(16) if nonce is None else nonce
    if not isinstance(request_nonce, str) or len(request_nonce) < 16:
        raise IdentityError("Nonce invalide.")
    message = _canonical(agent_id, issued_at, request_nonce, payload)
    signature = hmac.new(key, message, hashlib.sha256).hexdigest()
    return {"agent_id": agent_id, "timestamp": issued_at, "nonce": request_nonce,
            "payload": payload, "signature": signature}


def verify_request(envelope: dict[str, Any], key_dir: Path = DEFAULT_KEY_DIR,
                   replay_db: Path = DEFAULT_REPLAY_DB, now: int | None = None) -> dict[str, Any]:
    """Vérifie signature, fenêtre temporelle et nonce unique ; refuse par défaut."""
    required = {"agent_id", "timestamp", "nonce", "payload", "signature"}
    if not isinstance(envelope, dict) or set(envelope) != required:
        raise IdentityError("Enveloppe d'identité invalide.")
    agent_id = envelope["agent_id"]
    if not isinstance(agent_id, str) or not agent_id or any(
        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in agent_id
    ):
        raise IdentityError("Identifiant d'agent invalide.")
    timestamp, nonce, signature = envelope["timestamp"], envelope["nonce"], envelope["signature"]
    if not isinstance(timestamp, int) or isinstance(timestamp, bool):
        raise IdentityError("Horodatage invalide.")
    current = int(time.time()) if now is None else int(now)
    if abs(current - timestamp) > MAX_CLOCK_SKEW_SECONDS:
        raise IdentityError("Signature expirée ou horloge désynchronisée.")
    if not isinstance(nonce, str) or len(nonce) < 16:
        raise IdentityError("Nonce invalide.")
    if not isinstance(signature, str) or len(signature) != 64:
        raise IdentityError("Signature invalide.")
    try:
        key = (key_dir / f"{agent_id}.key").read_bytes()
    except OSError as exc:
        raise IdentityError("Identité inconnue ou clé indisponible.") from exc
    expected = hmac.new(key, _canonical(agent_id, timestamp, nonce, envelope["payload"]),
                        hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise IdentityError("Signature cryptographique incorrecte.")
    replay_db.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with sqlite3.connect(replay_db, timeout=10) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE IF NOT EXISTS used_nonces (agent_id TEXT NOT NULL, nonce TEXT NOT NULL, expires_at INTEGER NOT NULL, PRIMARY KEY(agent_id, nonce))")
        connection.execute("DELETE FROM used_nonces WHERE expires_at < ?", (current,))
        try:
            connection.execute("INSERT INTO used_nonces(agent_id, nonce, expires_at) VALUES (?, ?, ?)",
                                (agent_id, nonce, timestamp + MAX_CLOCK_SKEW_SECONDS))
        except sqlite3.IntegrityError as exc:
            raise IdentityError("Rejeu détecté : nonce déjà utilisé.") from exc
    try:
        os.chmod(replay_db, 0o600)
    except OSError:
        pass
    return {"authenticated": True, "agent_id": agent_id, "algorithm": "HMAC-SHA256",
            "replay_protected": True, "timestamp": timestamp}
