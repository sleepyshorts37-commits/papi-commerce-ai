"""Non-destructive rclone copy and verification for encrypted backup artifacts."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
from datetime import datetime, timezone
import subprocess
from typing import Any


class PapiKidsOffsiteBackupError(ValueError):
    """Offsite copy is not configured or verification failed."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory(backup_dir: Path) -> list[str]:
    pairs = []
    for encrypted in sorted(backup_dir.glob("*.pgdump.aesgcm")):
        manifest_path = Path(str(encrypted) + ".json")
        if not manifest_path.is_file():
            raise PapiKidsOffsiteBackupError("Manifeste absent pour une sauvegarde chiffrée.")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise PapiKidsOffsiteBackupError("Manifeste de sauvegarde illisible.") from exc
        if manifest.get("backup_file") != encrypted.name or manifest.get("encrypted") is not True:
            raise PapiKidsOffsiteBackupError("Manifeste non lié à la sauvegarde.")
        digest = _sha256(encrypted)
        if digest != manifest.get("encrypted_sha256"):
            raise PapiKidsOffsiteBackupError("SHA-256 chiffré incorrect ; copie refusée.")
        pairs.extend([encrypted.name, manifest_path.name])
    if not pairs:
        raise PapiKidsOffsiteBackupError("Aucune sauvegarde chiffrée à transférer.")
    return pairs


def copy_encrypted_backups_offsite(
    backup_dir: str | Path,
    *,
    remote: str,
    config_env: str = "RCLONE_CONFIG",
    rclone_binary: str = "rclone",
    enabled: bool = False,
    timeout_seconds: int = 3600,
) -> dict[str, Any]:
    """Copy and verify only encrypted dump + JSON manifest files; never sync/delete."""
    if enabled is not True:
        raise PapiKidsOffsiteBackupError("Transfert hors site désactivé explicitement.")
    if not isinstance(remote, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+:[A-Za-z0-9_./-]+", remote) or ".." in remote:
        raise PapiKidsOffsiteBackupError("Destination distante invalide.")
    if not isinstance(timeout_seconds, int) or not 30 <= timeout_seconds <= 86400:
        raise PapiKidsOffsiteBackupError("Délai de transfert hors limites.")
    raw_dir = Path(backup_dir)
    if raw_dir.is_symlink():
        raise PapiKidsOffsiteBackupError("Le dossier de sauvegarde ne peut pas être un lien symbolique.")
    directory = raw_dir.resolve()
    if not directory.is_dir():
        raise PapiKidsOffsiteBackupError("Volume de sauvegarde absent.")
    config_value = os.environ.get(config_env, "")
    if not config_value:
        raise PapiKidsOffsiteBackupError("Configuration rclone absente.")
    config_raw = Path(config_value)
    if config_raw.is_symlink() or not config_raw.is_file():
        raise PapiKidsOffsiteBackupError("Fichier de configuration rclone absent ou symbolique.")
    config_stat = config_raw.stat()
    if stat.S_IMODE(config_stat.st_mode) & 0o027:
        raise PapiKidsOffsiteBackupError("Le fichier rclone doit être privé (mode 0600 ou 0640).")
    if config_stat.st_uid != os.getuid() and config_stat.st_gid != os.getgid():
        raise PapiKidsOffsiteBackupError("Le fichier rclone n'est pas lisible par l'utilisateur du conteneur.")
    executable = shutil.which(rclone_binary)
    if not executable:
        raise PapiKidsOffsiteBackupError("Binaire rclone introuvable.")
    filenames = _inventory(directory)
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": "C.UTF-8",
        "RCLONE_CONFIG": str(config_raw.resolve()),
    }
    base = [
        executable, "--config", str(config_raw.resolve()),
        "--log-level", "ERROR",
    ]
    copy_command = base + [
        "copy", str(directory), remote,
        "--include", "*.pgdump.aesgcm",
        "--include", "*.pgdump.aesgcm.json",
        "--immutable", "--checksum",
        "--transfers", "2", "--checkers", "4",
    ]
    check_command = base + [
        "check", str(directory), remote,
        "--include", "*.pgdump.aesgcm",
        "--include", "*.pgdump.aesgcm.json",
        "--one-way", "--checksum",
    ]
    for command in (copy_command, check_command):
        try:
            result = subprocess.run(
                command, env=environment, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=timeout_seconds, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise PapiKidsOffsiteBackupError("Le transfert ou sa vérification a dépassé le délai.") from exc
        except OSError as exc:
            raise PapiKidsOffsiteBackupError("Impossible de lancer rclone.") from exc
        if result.returncode != 0:
            raise PapiKidsOffsiteBackupError(
                "La copie hors site ou sa vérification a échoué ; détails sensibles masqués."
            )
    verified_at = datetime.now(timezone.utc).isoformat()
    backup_records = []
    for encrypted in sorted(directory.glob("*.pgdump.aesgcm")):
        manifest_path = Path(str(encrypted) + ".json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        evidence_ref = hashlib.sha256(
            f"{encrypted.name}:{manifest['encrypted_sha256']}:{remote}:{verified_at}".encode("utf-8")
        ).hexdigest()
        backup_records.append({
            "backup_file": encrypted.name,
            "encrypted_sha256": manifest["encrypted_sha256"],
            "offsite_copy_verified": True,
            "offsite_evidence_ref": evidence_ref,
        })
    verification = {
        "schema_version": 1,
        "status": "offsite_copy_verified",
        "verified_at": verified_at,
        "remote": remote,
        "checksum_verified": True,
        "backups": backup_records,
        "files_copied_and_checked": len(filenames),
        "remote_deletions_performed": False,
    }
    report_path = directory / "offsite-verification.json"
    fd, temporary = tempfile.mkstemp(prefix=".offsite-proof-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(verification, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, report_path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return {
        "status": "offsite_copy_verified",
        "remote": remote,
        "files_copied_and_checked": len(filenames),
        "encrypted_only": True,
        "checksum_verified": True,
        "remote_deletions_performed": False,
        "source_files_deleted": False,
        "verification_report_path": str(report_path),
        "verification_report": verification,
    }
