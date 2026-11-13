"""Identité Ed25519 et registre de clés publiques versionné (socle local)."""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

DEFAULT_PRIVATE_DIR = Path.home() / ".papi" / "identity" / "ed25519"
DEFAULT_PUBLIC_REGISTRY = Path.home() / ".papi" / "identity" / "public-keys.json"
DEFAULT_REPLAY_DB = Path.home() / ".papi" / "identity" / "ed25519-replay.sqlite3"
MAX_CLOCK_SKEW_SECONDS = 300
_ALLOWED = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")


class Ed25519IdentityError(ValueError):
    """Identité Ed25519 invalide ou registre non sûr."""


def _validate_agent(agent_id: str) -> None:
    if not isinstance(agent_id, str) or not agent_id or any(c not in _ALLOWED for c in agent_id):
        raise Ed25519IdentityError("Identifiant d'agent invalide.")


def _canonical(agent_id: str, version: int, timestamp: int, nonce: str,
               payload: dict[str, Any]) -> bytes:
    if not isinstance(payload, dict):
        raise Ed25519IdentityError("Le contenu signé doit être un objet.")
    body = {"agent_id": agent_id, "key_version": version, "timestamp": timestamp,
            "nonce": nonce, "payload": payload}
    try:
        return json.dumps(body, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise Ed25519IdentityError("Contenu non sérialisable.") from exc


def _read_registry(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Ed25519IdentityError("Registre de clés absent ou illisible : accès fermé.") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("agents"), dict):
        raise Ed25519IdentityError("Registre de clés invalide : accès fermé.")
    return data


def _write_registry(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_name(path.name + "." + secrets.token_hex(8) + ".tmp")
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, sort_keys=True, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        os.chmod(path, 0o600)
    finally:
        temp.unlink(missing_ok=True)


def provision_ed25519_agent(agent_id: str, private_dir: Path = DEFAULT_PRIVATE_DIR,
                            registry_path: Path = DEFAULT_PUBLIC_REGISTRY) -> Path:
    """Crée une clé privée locale et publie uniquement sa clé publique."""
    _validate_agent(agent_id)
    private_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(private_dir, 0o700)
    private_path = private_dir / (agent_id + ".ed25519.pem")
    if private_path.exists():
        raise Ed25519IdentityError("Clé privée existante ; utiliser la rotation.")
    registry = _read_registry(registry_path) if registry_path.exists() else {"schema_version": 1, "agents": {}}
    if agent_id in registry["agents"]:
        raise Ed25519IdentityError("Agent déjà présent dans le registre ; utiliser la rotation.")
    key = Ed25519PrivateKey.generate()
    private_bytes = key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    fd = os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(private_bytes)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        private_path.unlink(missing_ok=True)
        raise
    public_bytes = key.public_key().public_bytes(serialization.Encoding.Raw,
                                                  serialization.PublicFormat.Raw)
    now = int(time.time())
    registry["agents"][agent_id] = {"status": "active", "key_version": 1,
        "public_key": public_bytes.hex(), "key_history": [{
            "key_version": 1, "public_key": public_bytes.hex(), "activated_at": now,
            "retired_at": None, "revoked_at": None}] }
    try:
        _write_registry(registry_path, registry)
    except Exception:
        private_path.unlink(missing_ok=True)
        raise
    return private_path


def rotate_ed25519_agent(agent_id: str, private_dir: Path = DEFAULT_PRIVATE_DIR,
                         registry_path: Path = DEFAULT_PUBLIC_REGISTRY) -> Path:
    """Incrémente la version de clé et invalide immédiatement l'ancienne clé."""
    _validate_agent(agent_id)
    registry = _read_registry(registry_path)
    current = registry["agents"].get(agent_id)
    if not isinstance(current, dict) or current.get("status") != "active":
        raise Ed25519IdentityError("Identité active inconnue.")
    private_path = private_dir / (agent_id + ".ed25519.pem")
    if not private_path.is_file():
        raise Ed25519IdentityError("Clé privée locale absente.")
    key = Ed25519PrivateKey.generate()
    private_bytes = key.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    temp = private_dir / ("." + agent_id + "." + secrets.token_hex(8) + ".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(private_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, private_path)
    finally:
        temp.unlink(missing_ok=True)
    public_bytes = key.public_key().public_bytes(serialization.Encoding.Raw,
                                                  serialization.PublicFormat.Raw)
    now = int(time.time())
    history = current.setdefault("key_history", [{
        "key_version": int(current["key_version"]), "public_key": current["public_key"],
        "activated_at": int(current.get("created_at", 0)), "retired_at": None,
        "revoked_at": None,
    }])
    if not isinstance(history, list) or not history:
        raise Ed25519IdentityError("Historique des clés invalide.")
    active_history = history[-1]
    if not isinstance(active_history, dict) or active_history.get("key_version") != int(current["key_version"]):
        raise Ed25519IdentityError("Version active absente de l'historique.")
    active_history["retired_at"] = now
    new_version = int(current["key_version"]) + 1
    history.append({"key_version": new_version, "public_key": public_bytes.hex(),
                    "activated_at": now, "retired_at": None, "revoked_at": None})
    registry["agents"][agent_id] = {"status": "active",
        "key_version": new_version, "public_key": public_bytes.hex(),
        "key_history": history}
    _write_registry(registry_path, registry)
    return private_path


def revoke_ed25519_agent(agent_id: str, registry_path: Path = DEFAULT_PUBLIC_REGISTRY) -> None:
    _validate_agent(agent_id)
    registry = _read_registry(registry_path)
    record = registry["agents"].get(agent_id)
    if not isinstance(record, dict):
        raise Ed25519IdentityError("Identité inconnue.")
    now = int(time.time())
    record["status"] = "revoked"
    record["revoked_at"] = now
    history = record.setdefault("key_history", [{
        "key_version": int(record["key_version"]), "public_key": record["public_key"],
        "activated_at": int(record.get("created_at", 0)), "retired_at": None,
        "revoked_at": None,
    }])
    if not isinstance(history, list) or not history:
        raise Ed25519IdentityError("Historique des clés invalide.")
    history[-1]["revoked_at"] = now
    _write_registry(registry_path, registry)


def sign_ed25519_request(agent_id: str, payload: dict[str, Any], private_path: Path,
                         key_version: int = 1, timestamp: int | None = None,
                         nonce: str | None = None) -> dict[str, Any]:
    _validate_agent(agent_id)
    try:
        key = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
    except (OSError, ValueError, TypeError) as exc:
        raise Ed25519IdentityError("Clé privée indisponible ou invalide.") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise Ed25519IdentityError("Type de clé privée incorrect.")
    issued = int(time.time()) if timestamp is None else int(timestamp)
    token = secrets.token_hex(16) if nonce is None else nonce
    if not isinstance(token, str) or len(token) < 16 or not isinstance(key_version, int) or key_version < 1:
        raise Ed25519IdentityError("Nonce ou version de clé invalide.")
    message = _canonical(agent_id, key_version, issued, token, payload)
    return {"agent_id": agent_id, "key_version": key_version, "timestamp": issued,
            "nonce": token, "payload": payload, "signature": key.sign(message).hex()}


def verify_ed25519_request(envelope: dict[str, Any], registry_path: Path = DEFAULT_PUBLIC_REGISTRY,
                           replay_db: Path = DEFAULT_REPLAY_DB, now: int | None = None) -> dict[str, Any]:
    required = {"agent_id", "key_version", "timestamp", "nonce", "payload", "signature"}
    if not isinstance(envelope, dict) or set(envelope) != required:
        raise Ed25519IdentityError("Enveloppe Ed25519 invalide.")
    agent_id, version = envelope["agent_id"], envelope["key_version"]
    _validate_agent(agent_id)
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise Ed25519IdentityError("Version de clé invalide.")
    timestamp, nonce, signature = envelope["timestamp"], envelope["nonce"], envelope["signature"]
    if not isinstance(timestamp, int) or isinstance(timestamp, bool):
        raise Ed25519IdentityError("Horodatage invalide.")
    current = int(time.time()) if now is None else int(now)
    if abs(current - timestamp) > MAX_CLOCK_SKEW_SECONDS:
        raise Ed25519IdentityError("Signature expirée ou horloge désynchronisée.")
    if not isinstance(nonce, str) or len(nonce) < 16:
        raise Ed25519IdentityError("Nonce invalide.")
    try:
        signature_bytes = bytes.fromhex(signature)
    except (TypeError, ValueError) as exc:
        raise Ed25519IdentityError("Signature invalide.") from exc
    if len(signature_bytes) != 64:
        raise Ed25519IdentityError("Signature invalide.")
    registry = _read_registry(registry_path)
    record = registry["agents"].get(agent_id)
    if not isinstance(record, dict) or record.get("status") != "active":
        raise Ed25519IdentityError("Identité inconnue ou révoquée.")
    if record.get("key_version") != version:
        raise Ed25519IdentityError("Version de clé révoquée ou obsolète.")
    try:
        public = bytes.fromhex(record["public_key"])
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(public).verify(
            signature_bytes, _canonical(agent_id, version, timestamp, nonce, envelope["payload"]))
    except (ValueError, KeyError, TypeError, InvalidSignature) as exc:
        raise Ed25519IdentityError("Signature Ed25519 incorrecte.") from exc
    replay_db.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with sqlite3.connect(replay_db, timeout=30) as connection:
        # Wait for concurrent writers; do not change journal mode per request.
        # Concurrent WAL initialization can fail with SQLITE_BUSY.
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("CREATE TABLE IF NOT EXISTS used_nonces (agent_id TEXT NOT NULL, nonce TEXT NOT NULL, expires_at INTEGER NOT NULL, PRIMARY KEY(agent_id, nonce))")
        connection.execute("DELETE FROM used_nonces WHERE expires_at < ?", (current,))
        try:
            connection.execute("INSERT INTO used_nonces VALUES (?, ?, ?)",
                               (agent_id, nonce, timestamp + MAX_CLOCK_SKEW_SECONDS))
        except sqlite3.IntegrityError as exc:
            raise Ed25519IdentityError("Rejeu détecté.") from exc
    os.chmod(replay_db, 0o600)
    return {"authenticated": True, "agent_id": agent_id, "key_version": version,
            "algorithm": "Ed25519", "replay_protected": True}


def verify_ed25519_signature(envelope: dict[str, Any],
                             registry_path: Path = DEFAULT_PUBLIC_REGISTRY) -> dict[str, Any]:
    """Vérifie une preuve conservée avec la clé publique correspondant à sa version.

    N'accepte une ancienne clé que pour les horodatages compris dans sa période
    d'activation. Cette vérification ne consomme pas le nonce et ne réactive
    jamais une ancienne clé pour signer de nouvelles requêtes.
    """
    required = {"agent_id", "key_version", "timestamp", "nonce", "payload", "signature"}
    if not isinstance(envelope, dict) or set(envelope) != required:
        raise Ed25519IdentityError("Enveloppe Ed25519 invalide.")
    agent_id, version = envelope["agent_id"], envelope["key_version"]
    _validate_agent(agent_id)
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise Ed25519IdentityError("Version de clé invalide.")
    timestamp, nonce, signature = envelope["timestamp"], envelope["nonce"], envelope["signature"]
    if not isinstance(timestamp, int) or isinstance(timestamp, bool):
        raise Ed25519IdentityError("Horodatage invalide.")
    if not isinstance(nonce, str) or len(nonce) < 16 or not isinstance(signature, str):
        raise Ed25519IdentityError("Nonce ou signature invalide.")
    try:
        signature_bytes = bytes.fromhex(signature)
    except ValueError as exc:
        raise Ed25519IdentityError("Signature invalide.") from exc
    if len(signature_bytes) != 64:
        raise Ed25519IdentityError("Signature invalide.")
    registry = _read_registry(registry_path)
    record = registry["agents"].get(agent_id)
    if not isinstance(record, dict):
        raise Ed25519IdentityError("Identité inconnue.")
    history = record.get("key_history")
    if not isinstance(history, list):
        # Backward compatibility for registries created before key history.
        history = [{
            "key_version": record.get("key_version"),
            "public_key": record.get("public_key"),
            "activated_at": 0, "retired_at": None,
            "revoked_at": record.get("revoked_at"),
        }]
    selected = next((item for item in history
                     if isinstance(item, dict) and item.get("key_version") == version), None)
    if selected is None:
        raise Ed25519IdentityError("Version de clé absente de l'historique.")
    activated = selected.get("activated_at", 0)
    retired = selected.get("retired_at")
    revoked = selected.get("revoked_at")
    if not isinstance(activated, int) or timestamp < activated:
        raise Ed25519IdentityError("Signature antérieure à l'activation de la clé.")
    end_times = [value for value in (retired, revoked) if value is not None]
    if any(not isinstance(value, int) for value in end_times):
        raise Ed25519IdentityError("Période de validité de clé invalide.")
    if end_times and timestamp > min(end_times):
        raise Ed25519IdentityError("Signature postérieure à la fin de validité de la clé.")
    try:
        public = bytes.fromhex(selected["public_key"])
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(public).verify(
            signature_bytes, _canonical(agent_id, version, timestamp, nonce, envelope["payload"]))
    except (ValueError, KeyError, TypeError, InvalidSignature) as exc:
        raise Ed25519IdentityError("Signature Ed25519 incorrecte.") from exc
    return {"authenticated": True, "agent_id": agent_id, "key_version": version,
            "algorithm": "Ed25519", "historical_verification": True}
