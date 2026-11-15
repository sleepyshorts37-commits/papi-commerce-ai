"""One-shot opt-in CLI for encrypted PostgreSQL backups."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
from typing import Any

from .papi_kids_backup_job import create_encrypted_postgres_backup, PapiKidsBackupJobError


class PapiKidsBackupRunnerError(ValueError):
    """Backup runner configuration is unsafe or incomplete."""


def run_backup_from_environment() -> dict[str, Any]:
    if os.environ.get("PAPI_KIDS_BACKUP_ENABLED", "false").lower() != "true":
        raise PapiKidsBackupRunnerError("Sauvegarde désactivée : PAPI_KIDS_BACKUP_ENABLED doit être true.")
    directory_value = os.environ.get("PAPI_KIDS_BACKUP_DIRECTORY", "")
    key_id = os.environ.get("PAPI_KIDS_BACKUP_KEY_ID", "")
    if not directory_value or not key_id:
        raise PapiKidsBackupRunnerError("Dossier de sauvegarde ou identifiant de clé absent.")
    raw = Path(directory_value)
    if raw.is_symlink():
        raise PapiKidsBackupRunnerError("Le dossier de sauvegarde ne peut pas être un lien symbolique.")
    directory = raw.resolve()
    if not directory.is_dir() or directory == Path("/") or not os.access(directory, os.W_OK | os.X_OK):
        raise PapiKidsBackupRunnerError("Volume de sauvegarde absent ou non accessible.")
    mode = stat.S_IMODE(directory.stat().st_mode)
    if mode & 0o077:
        raise PapiKidsBackupRunnerError("Le volume de sauvegarde doit être privé (aucun accès groupe/autres).")
    try:
        return create_encrypted_postgres_backup(
            directory, key_id=key_id,
        )
    except PapiKidsBackupJobError as exc:
        raise PapiKidsBackupRunnerError("La sauvegarde PostgreSQL chiffrée a échoué.") from exc


def main() -> int:
    result = run_backup_from_environment()
    print(json.dumps({
        "status": "backup_created",
        "backup_file": Path(result["backup_path"]).name,
        "manifest_file": Path(result["manifest_path"]).name,
        "encrypted": True,
        "plaintext_staging_deleted": result["plaintext_staging_deleted"],
        "offsite_upload_performed": False,
    }, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
