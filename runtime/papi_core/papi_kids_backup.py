"""Streaming AES-256-GCM encryption and integrity verification for pg_dump archives."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from datetime import datetime, timezone
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_MAGIC = b"PAPIKDPBK1"
_NONCE_BYTES = 12
_TAG_BYTES = 16
_CHUNK_BYTES = 1024 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class PapiKidsBackupError(ValueError):
    """Backup encryption, integrity or decryption failed."""


def _key_from_env(key_env: str) -> bytes:
    encoded = os.environ.get(key_env, "")
    try:
        key = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise PapiKidsBackupError("Clé de sauvegarde absente ou encodage invalide.") from exc
    if len(key) != 32:
        raise PapiKidsBackupError("La clé AES-256 doit contenir exactement 32 octets.")
    return key


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_target(directory: Path, prefix: str, suffix: str) -> tuple[int, str]:
    return tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=directory)


def encrypt_pg_dump_archive(
    archive_path: str | Path,
    backup_dir: str | Path,
    *,
    key_env: str = "PAPI_KIDS_BACKUP_KEY_B64",
    key_id: str,
) -> dict[str, Any]:
    """Encrypt a custom-format pg_dump archive; output and manifest are private."""
    source = Path(archive_path).resolve()
    target_dir = Path(backup_dir).resolve()
    if not source.is_file() or not target_dir.is_dir():
        raise PapiKidsBackupError("Archive source ou dossier de sauvegarde introuvable.")
    if not isinstance(key_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", key_id):
        raise PapiKidsBackupError("Identifiant de clé invalide.")
    key = _key_from_env(key_env)
    with source.open("rb") as stream:
        if stream.read(5) != b"PGDMP":
            raise PapiKidsBackupError("Le fichier source n'est pas une archive pg_dump custom.")
    nonce = os.urandom(_NONCE_BYTES)
    key_id_bytes = key_id.encode("ascii")
    header = _MAGIC + bytes([len(key_id_bytes)]) + key_id_bytes + nonce
    encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    encryptor.authenticate_additional_data(_MAGIC + key_id_bytes)
    backup_name = f"papi-kids-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{os.urandom(4).hex()}.pgdump.aesgcm"
    backup_path = target_dir / backup_name
    fd, temporary = _atomic_target(target_dir, ".backup-", ".tmp")
    try:
        with os.fdopen(fd, "wb") as output, source.open("rb") as input_stream:
            output.write(header)
            for chunk in iter(lambda: input_stream.read(_CHUNK_BYTES), b""):
                output.write(encryptor.update(chunk))
            output.write(encryptor.finalize())
            output.write(encryptor.tag)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, backup_path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    manifest = {
        "schema_version": 1,
        "backup_file": backup_name,
        "format": "pg_dump_custom_aes_256_gcm",
        "key_id": key_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "encrypted": True,
        "source_size_bytes": source.stat().st_size,
        "encrypted_size_bytes": backup_path.stat().st_size,
        "source_sha256": _hash_file(source),
        "encrypted_sha256": _hash_file(backup_path),
        "authentication": "AES-256-GCM",
    }
    manifest_path = target_dir / f"{backup_name}.json"
    fd, temporary_manifest = _atomic_target(target_dir, ".manifest-", ".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary_manifest, 0o600)
        os.replace(temporary_manifest, manifest_path)
    except Exception:
        try:
            os.unlink(temporary_manifest)
        except FileNotFoundError:
            pass
        backup_path.unlink(missing_ok=True)
        raise
    return {
        "backup_path": str(backup_path),
        "manifest_path": str(manifest_path),
        "manifest": manifest,
        "plaintext_removed": False,
        "offsite_copy_performed": False,
    }


def decrypt_and_verify_pg_dump_archive(
    backup_path: str | Path,
    manifest_path: str | Path,
    output_path: str | Path,
    *,
    key_env: str = "PAPI_KIDS_BACKUP_KEY_B64",
) -> dict[str, Any]:
    """Authenticate, decrypt and verify a pg_dump archive into a private file."""
    encrypted = Path(backup_path).resolve()
    manifest_file = Path(manifest_path).resolve()
    output = Path(output_path).resolve()
    if not encrypted.is_file() or not manifest_file.is_file():
        raise PapiKidsBackupError("Sauvegarde chiffrée ou manifeste absent.")
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PapiKidsBackupError("Manifeste de sauvegarde invalide.") from exc
    if manifest.get("encrypted_sha256") != _hash_file(encrypted):
        raise PapiKidsBackupError("Empreinte de sauvegarde chiffrée incorrecte.")
    if manifest.get("backup_file") != encrypted.name or manifest.get("encrypted") is not True:
        raise PapiKidsBackupError("Manifeste non lié à cette sauvegarde.")
    key = _key_from_env(key_env)
    fd, temporary = _atomic_target(output.parent, ".restore-", ".tmp")
    try:
        with encrypted.open("rb") as input_stream:
            magic = input_stream.read(len(_MAGIC))
            key_id_length_raw = input_stream.read(1)
            if magic != _MAGIC or len(key_id_length_raw) != 1:
                raise PapiKidsBackupError("En-tête de sauvegarde inconnu.")
            key_id_length = key_id_length_raw[0]
            key_id_bytes = input_stream.read(key_id_length)
            nonce = input_stream.read(_NONCE_BYTES)
            if not key_id_length or len(key_id_bytes) != key_id_length or len(nonce) != _NONCE_BYTES:
                raise PapiKidsBackupError("En-tête de sauvegarde tronqué.")
            if key_id_bytes.decode("ascii", errors="strict") != manifest.get("key_id"):
                raise PapiKidsBackupError("Identifiant de clé différent du manifeste.")
            total_size = encrypted.stat().st_size
            header_size = len(_MAGIC) + 1 + key_id_length + _NONCE_BYTES
            cipher_size = total_size - header_size - _TAG_BYTES
            if cipher_size < 5:
                raise PapiKidsBackupError("Archive chiffrée tronquée.")
            input_stream.seek(total_size - _TAG_BYTES)
            tag = input_stream.read(_TAG_BYTES)
            input_stream.seek(header_size)
            decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
            decryptor.authenticate_additional_data(_MAGIC + key_id_bytes)
            with os.fdopen(fd, "wb") as output_stream:
                remaining = cipher_size
                while remaining:
                    chunk = input_stream.read(min(_CHUNK_BYTES, remaining))
                    if not chunk:
                        raise PapiKidsBackupError("Corps de sauvegarde tronqué.")
                    remaining -= len(chunk)
                    output_stream.write(decryptor.update(chunk))
                output_stream.write(decryptor.finalize())
                output_stream.flush()
                os.fsync(output_stream.fileno())
        os.chmod(temporary, 0o600)
        restored = Path(temporary)
        if restored.read_bytes()[:5] != b"PGDMP":
            raise PapiKidsBackupError("Le contenu déchiffré n'est pas une archive pg_dump.")
        if _hash_file(restored) != manifest.get("source_sha256"):
            raise PapiKidsBackupError("L'empreinte de l'archive restaurée ne correspond pas.")
        os.replace(temporary, output)
    except Exception as exc:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        if isinstance(exc, PapiKidsBackupError):
            raise
        raise PapiKidsBackupError("Authentification ou déchiffrement de sauvegarde échoué.") from exc
    return {
        "restored_path": str(output),
        "source_sha256_verified": True,
        "gcm_authentication_verified": True,
        "pg_dump_custom_header_verified": True,
        "database_restore_performed": False,
    }
