"""Local Ed25519 key lifecycle for external audit checkpoint signatures.

Private keys remain in a trusted backend filesystem. The JSON registry contains
public verification material only. Retired keys remain verifiable for historical
records; revoked keys fail closed and cannot verify or sign.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import stat
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

_KEY_ID = re.compile(r"audit-[0-9a-f]{32}")
_PUBLIC_KEY_BYTES = 32
_SIGNATURE_BYTES = 64


class AuditKeyError(ValueError):
    """Audit signing key or public registry is invalid or unavailable."""


class LocalAuditKeyring:
    """Filesystem keyring; instantiate only inside a trusted backend boundary."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.private_dir = self.root / "private"
        self.registry_path = self.root / "public-keys.json"

    def _load_registry(self) -> dict[str, Any]:
        try:
            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AuditKeyError("Registre de clés absent ou illisible : accès fermé.") from exc
        if (not isinstance(data, dict) or set(data) != {"schema_version", "keys"}
                or type(data["schema_version"]) is not int or data["schema_version"] != 1
                or not isinstance(data["keys"], dict)):
            raise AuditKeyError("Registre de clés invalide : accès fermé.")
        active = 0
        for key_id, entry in data["keys"].items():
            if not isinstance(key_id, str) or not _KEY_ID.fullmatch(key_id):
                raise AuditKeyError("Identifiant de clé invalide dans le registre.")
            if (not isinstance(entry, dict)
                    or set(entry) - {"public_key", "status", "created_at", "retired_at", "revoked_at"}
                    or not {"public_key", "status", "created_at"} <= set(entry)
                    or not isinstance(entry["status"], str)
                    or entry["status"] not in {"active", "retired", "revoked"}):
                raise AuditKeyError("Entrée de clé invalide dans le registre.")
            try:
                public = bytes.fromhex(entry["public_key"])
            except (TypeError, ValueError) as exc:
                raise AuditKeyError("Clé publique mal formée.") from exc
            if len(public) != _PUBLIC_KEY_BYTES:
                raise AuditKeyError("Longueur de clé publique invalide.")
            if entry["status"] == "active":
                active += 1
        if active > 1:
            raise AuditKeyError("Plusieurs clés de signature actives : accès fermé.")
        return data

    def _save_registry(self, data: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)
        temp = self.root / (".public-keys-" + secrets.token_hex(8) + ".tmp")
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, sort_keys=True, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self.registry_path)
            os.chmod(self.registry_path, 0o600)
            dir_fd = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        finally:
            temp.unlink(missing_ok=True)

    def provision(self) -> str:
        """Create the first signing key; never overwrites an existing registry."""
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)
        if self.registry_path.exists():
            raise AuditKeyError("Registre existant : utiliser rotate().")
        self.private_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.private_dir, 0o700)
        key = Ed25519PrivateKey.generate()
        key_id = "audit-" + secrets.token_hex(16)
        private_path = self.private_dir / (key_id + ".pem")
        private_bytes = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        fd = os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(private_bytes)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            private_path.unlink(missing_ok=True)
            raise
        public = key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        try:
            self._save_registry({"schema_version": 1, "keys": {
                key_id: {"public_key": public.hex(), "status": "active", "created_at": __import__("time").time_ns()}
            }})
        except Exception:
            private_path.unlink(missing_ok=True)
            raise
        return key_id

    def rotate(self, current_key_id: str) -> str:
        """Retire the active key and create a new key; retain old public material."""
        data = self._load_registry()
        current = data["keys"].get(current_key_id)
        if not isinstance(current, dict) or current.get("status") != "active":
            raise AuditKeyError("La clé à remplacer n'est pas active.")
        new_id = "audit-" + secrets.token_hex(16)
        key = Ed25519PrivateKey.generate()
        self.private_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.private_dir, 0o700)
        private_path = self.private_dir / (new_id + ".pem")
        private_bytes = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        fd = os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(private_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            public = key.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            )
            current["status"] = "retired"
            current["retired_at"] = __import__("time").time_ns()
            data["keys"][new_id] = {
                "public_key": public.hex(), "status": "active",
                "created_at": __import__("time").time_ns(),
            }
            self._save_registry(data)
        except Exception:
            private_path.unlink(missing_ok=True)
            raise
        return new_id

    def revoke(self, key_id: str) -> None:
        """Revoke one key immediately; revocation overrides historical retention."""
        data = self._load_registry()
        entry = data["keys"].get(key_id)
        if not isinstance(entry, dict) or entry.get("status") == "revoked":
            raise AuditKeyError("Clé inconnue ou déjà révoquée.")
        entry["status"] = "revoked"
        entry["revoked_at"] = __import__("time").time_ns()
        self._save_registry(data)

    def sign(self, key_id: str, message: bytes) -> str:
        """Sign bytes with the active key only; returns a 128-character hex signature."""
        data = self._load_registry()
        entry = data["keys"].get(key_id)
        if not isinstance(entry, dict) or entry.get("status") != "active":
            raise AuditKeyError("La clé de signature n'est pas active.")
        path = self.private_dir / (key_id + ".pem")
        descriptor = None
        try:
            nofollow = getattr(os, "O_NOFOLLOW", None)
            if nofollow is None:
                raise AuditKeyError("La plateforme ne permet pas de refuser les liens symboliques.")
            descriptor = os.open(path, os.O_RDONLY | nofollow | getattr(os, "O_NONBLOCK", 0))
            info = os.fstat(descriptor)
            if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077
                    or (hasattr(os, "geteuid") and info.st_uid != os.geteuid())):
                raise AuditKeyError("Permissions ou propriétaire de clé privée invalides.")
            with os.fdopen(descriptor, "rb") as handle:
                descriptor = None
                private_bytes = handle.read()
            key = serialization.load_pem_private_key(private_bytes, password=None)
        except (OSError, ValueError, TypeError) as exc:
            raise AuditKeyError("Clé privée absente ou invalide.") from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
        if not isinstance(key, Ed25519PrivateKey):
            raise AuditKeyError("Type de clé privée incorrect.")
        if not isinstance(message, bytes):
            raise AuditKeyError("Le contenu à signer doit être en octets.")
        expected_public = bytes.fromhex(entry["public_key"])
        actual_public = key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        if actual_public != expected_public:
            raise AuditKeyError("La clé privée ne correspond pas au registre public.")
        return key.sign(message).hex()

    def verify(self, key_id: str, message: bytes, signature_hex: str) -> bool:
        """Verify active or retired keys; revoked/unknown keys fail closed."""
        data = self._load_registry()
        entry = data["keys"].get(key_id)
        if not isinstance(entry, dict) or entry.get("status") not in {"active", "retired"}:
            return False
        try:
            signature = bytes.fromhex(signature_hex)
            public = bytes.fromhex(entry["public_key"])
            if len(signature) != _SIGNATURE_BYTES or len(public) != _PUBLIC_KEY_BYTES:
                return False
            Ed25519PublicKey.from_public_bytes(public).verify(signature, message)
            return True
        except (TypeError, ValueError, InvalidSignature):
            return False
