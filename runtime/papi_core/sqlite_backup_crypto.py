"""Chiffrement authentifié AES-256-GCM et gestion locale des clés de sauvegarde."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .sqlite_backup import BackupRestoreError, _integrity, _write_exclusive

_FORMAT_VERSION = 2
_ALGORITHM = "AES-256-GCM"
_KEY_BYTES = 32
_NONCE_BYTES = 12
_MAX_ENCRYPTED_BYTES = 256 * 1024 * 1024


class BackupEncryptionError(ValueError):
    """Erreur de chiffrement ou de gestion de clé."""


def generate_backup_key(key_path: Path) -> dict[str, Any]:
    """Crée une clé aléatoire 256 bits dans un fichier local exclusif, jamais dans le dépôt."""
    path = Path(key_path)
    if path.is_symlink() or path.exists():
        raise BackupEncryptionError("Le chemin de clé doit être absent et ne pas être un lien symbolique.")
    if path.parent.is_symlink() or (path.parent.exists() and not path.parent.is_dir()):
        raise BackupEncryptionError("Répertoire de clé invalide.")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    key = secrets.token_bytes(_KEY_BYTES)
    try:
        _write_exclusive(path, key, 0o600)
        os.chmod(path, 0o600)
    except OSError as exc:
        raise BackupEncryptionError("Création de la clé impossible.") from exc
    return {"status": "key_created", "key_path": str(path),
            "key_id": hashlib.sha256(key).hexdigest()[:16],
            "algorithm": _ALGORITHM, "key_bytes": _KEY_BYTES,
            "secret_returned": False}


def _load_key(key_path: Path) -> bytes:
    path = Path(key_path)
    if path.is_symlink() or not path.is_file():
        raise BackupEncryptionError("Fichier de clé absent ou lien symbolique interdit.")
    try:
        if os.name == "posix":
            mode = stat.S_IMODE(path.stat().st_mode)
            if mode & 0o077:
                raise BackupEncryptionError("Permissions de clé trop ouvertes ; appliquer chmod 600.")
        key = path.read_bytes()
    except OSError as exc:
        raise BackupEncryptionError("Lecture de la clé impossible.") from exc
    if len(key) != _KEY_BYTES:
        raise BackupEncryptionError("La clé doit contenir exactement 32 octets.")
    return key


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _exclusive_bytes(path: Path, content: bytes) -> None:
    if path.is_symlink() or path.exists():
        raise BackupEncryptionError("La destination existe déjà ; aucun écrasement n'est autorisé.")
    if path.parent.is_symlink() or (path.parent.exists() and not path.parent.is_dir()):
        raise BackupEncryptionError("Répertoire de destination invalide.")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        _write_exclusive(path, content, 0o600)
        os.chmod(path, 0o600)
    except FileExistsError as exc:
        raise BackupEncryptionError("La destination existe déjà.") from exc
    except OSError as exc:
        raise BackupEncryptionError("Écriture sécurisée impossible.") from exc


def _manifest_aad(manifest: dict[str, Any]) -> dict[str, Any]:
    """Construit les données associées authentifiées, avec compatibilité lecture v1."""
    core = {key: manifest[key] for key in (
        "format_version", "algorithm", "key_id", "encrypted_file", "nonce"
    )}
    if manifest["format_version"] == 1:
        return core
    return {**core, "created_at": manifest["created_at"],
            "ciphertext_size": manifest["ciphertext_size"],
            "plaintext_size": manifest["plaintext_size"]}


def _manifest_header(manifest: dict[str, Any]) -> dict[str, Any]:
    """Alias interne conservé pour les appels de déchiffrement."""
    return _manifest_aad(manifest)


def encrypt_sqlite_backup(backup_path: Path, key_path: Path,
                          manifest_path: Path) -> dict[str, Any]:
    """Chiffre un snapshot SQLite AES-256-GCM ; les fichiers source restent inchangés."""
    source = Path(backup_path)
    if source.is_symlink() or not source.is_file():
        raise BackupEncryptionError("Sauvegarde source absente ou lien symbolique interdit.")
    try:
        _integrity(source)
        size = source.stat().st_size
        if size <= 0 or size > _MAX_ENCRYPTED_BYTES:
            raise BackupEncryptionError("Taille hors limite du chiffrement (256 Mio).")
        plaintext = source.read_bytes()
        key = _load_key(key_path)
        nonce = secrets.token_bytes(_NONCE_BYTES)
        encrypted_path = Path(str(manifest_path)[:-len(".manifest.json")] + ".enc") if str(manifest_path).endswith(".manifest.json") else Path(str(manifest_path) + ".enc")
        created_at = datetime.now(timezone.utc).isoformat()
        header = {"format_version": _FORMAT_VERSION, "algorithm": _ALGORITHM,
                  "key_id": hashlib.sha256(key).hexdigest()[:16],
                  "encrypted_file": encrypted_path.name, "nonce": nonce.hex(),
                  "created_at": created_at, "ciphertext_size": len(plaintext) + 16,
                  "plaintext_size": len(plaintext)}
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, _canonical(header))
        manifest = {**header, "ciphertext_sha256": hashlib.sha256(ciphertext).hexdigest()}
        _exclusive_bytes(encrypted_path, ciphertext)
        try:
            _exclusive_bytes(Path(manifest_path), _canonical(manifest) + b"\n")
        except Exception:
            encrypted_path.unlink(missing_ok=True)
            raise
        return {"status": "encrypted", "encrypted_path": str(encrypted_path),
                "manifest_path": str(manifest_path), "key_id": header["key_id"],
                "algorithm": _ALGORITHM, "plaintext_size": len(plaintext),
                "ciphertext_size": len(ciphertext)}
    except BackupRestoreError as exc:
        raise BackupEncryptionError("La sauvegarde source n'est pas intègre.") from exc
    except OSError as exc:
        raise BackupEncryptionError("Lecture ou chiffrement de la sauvegarde impossible.") from exc


def _read_encrypted(manifest_path: Path, key_path: Path) -> tuple[bytes, bytes, dict[str, Any]]:
    manifest_file = Path(manifest_path)
    if manifest_file.is_symlink() or not manifest_file.is_file():
        raise BackupEncryptionError("Manifeste chiffré absent ou lien symbolique interdit.")
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise BackupEncryptionError("Manifeste invalide.")
        version = manifest.get("format_version")
        if type(version) is not int or version not in (1, _FORMAT_VERSION):
            raise BackupEncryptionError("Version de manifeste invalide.")
        legacy_fields = {"format_version", "algorithm", "key_id", "encrypted_file", "nonce",
                         "created_at", "ciphertext_size", "ciphertext_sha256", "plaintext_size"}
        if set(manifest) != legacy_fields:
            raise BackupEncryptionError("Champs du manifeste absents ou inattendus.")
        if manifest.get("algorithm") != _ALGORITHM:
            raise BackupEncryptionError("Algorithme de chiffrement non pris en charge.")
        name = manifest.get("encrypted_file")
        if not isinstance(name, str) or Path(name).name != name or not name.endswith(".enc") or name in (".enc", "..enc"):
            raise BackupEncryptionError("Nom de fichier chiffré invalide.")
        if not isinstance(manifest.get("key_id"), str) or len(manifest["key_id"]) != 16:
            raise BackupEncryptionError("Identifiant de clé invalide.")
        if not isinstance(manifest.get("created_at"), str) or len(manifest["created_at"]) > 64:
            raise BackupEncryptionError("Horodatage du manifeste invalide.")
        try:
            datetime.fromisoformat(manifest["created_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise BackupEncryptionError("Horodatage du manifeste invalide.") from exc
        if type(manifest.get("plaintext_size")) is not int or not (0 < manifest["plaintext_size"] <= _MAX_ENCRYPTED_BYTES):
            raise BackupEncryptionError("Taille du contenu clair invalide.")
        if type(manifest.get("ciphertext_size")) is not int or manifest["ciphertext_size"] != manifest["plaintext_size"] + 16:
            raise BackupEncryptionError("Taille du contenu chiffré invalide.")
        if not isinstance(manifest.get("ciphertext_sha256"), str) or len(manifest["ciphertext_sha256"]) != 64:
            raise BackupEncryptionError("Empreinte du contenu chiffré invalide.")
        nonce_value = manifest.get("nonce")
        if not isinstance(nonce_value, str) or len(nonce_value) != _NONCE_BYTES * 2:
            raise BackupEncryptionError("Nonce AES-GCM invalide.")
        nonce = bytes.fromhex(nonce_value)
        encrypted = manifest_file.parent / name
        if encrypted.is_symlink() or not encrypted.is_file():
            raise BackupEncryptionError("Fichier chiffré absent ou lien symbolique interdit.")
        ciphertext = encrypted.read_bytes()
        if len(ciphertext) != manifest["ciphertext_size"] or hashlib.sha256(ciphertext).hexdigest() != manifest["ciphertext_sha256"]:
            raise BackupEncryptionError("Intégrité du fichier chiffré incorrecte.")
        key = _load_key(key_path)
        key_id = hashlib.sha256(key).hexdigest()[:16]
        if key_id != manifest.get("key_id"):
            raise BackupEncryptionError("Cette clé ne correspond pas au manifeste.")
        return ciphertext, key, manifest
    except BackupEncryptionError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise BackupEncryptionError("Manifeste ou données chiffrées invalides.") from exc
