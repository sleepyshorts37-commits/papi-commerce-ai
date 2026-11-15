"""Explicitly authorized restore drill into a dedicated disposable PostgreSQL database."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

from .papi_kids_backup import decrypt_and_verify_pg_dump_archive, PapiKidsBackupError
from .papi_kids_backup_job import _database_environment, PapiKidsBackupJobError


class PapiKidsRestoreDrillError(ValueError):
    """Restore drill refused or failed safely."""


def run_isolated_restore_drill(
    backup_path: str | Path,
    manifest_path: str | Path,
    staging_dir: str | Path,
    *,
    restore_database_url_env: str = "PAPI_KIDS_RESTORE_TEST_DATABASE_URL",
    production_database_url_env: str = "PAPI_KIDS_DATABASE_URL",
    key_env: str = "PAPI_KIDS_BACKUP_KEY_B64",
    pg_restore_binary: str = "pg_restore",
    expected_database_name: str,
    restore_authorized: bool = False,
    timeout_seconds: int = 3600,
) -> dict[str, Any]:
    """Restore only to an explicitly named *_restore_test or *_drill database."""
    if restore_authorized is not True:
        raise PapiKidsRestoreDrillError("Autorisation explicite de restauration de test requise.")
    if not isinstance(expected_database_name, str) or not (
        expected_database_name.endswith("_restore_test") or expected_database_name.endswith("_drill")
    ):
        raise PapiKidsRestoreDrillError("La base cible doit se terminer par _restore_test ou _drill.")
    if not isinstance(timeout_seconds, int) or not 30 <= timeout_seconds <= 86400:
        raise PapiKidsRestoreDrillError("Délai de restauration hors limites.")
    restore_url = os.environ.get(restore_database_url_env, "")
    if not restore_url:
        raise PapiKidsRestoreDrillError("URL de base de restauration de test absente.")
    try:
        target_env = _database_environment(restore_url)
        production_url = os.environ.get(production_database_url_env, "")
        production_name = _database_environment(production_url)["PGDATABASE"] if production_url else None
    except PapiKidsBackupJobError as exc:
        raise PapiKidsRestoreDrillError("Configuration PostgreSQL/TLS invalide.") from exc
    target_name = target_env["PGDATABASE"]
    if target_name != expected_database_name:
        raise PapiKidsRestoreDrillError("Le nom de base cible ne correspond pas à la confirmation.")
    if target_name == production_name:
        raise PapiKidsRestoreDrillError("La restauration vers la base de production est interdite.")

    target_dir = Path(staging_dir).resolve()
    if not target_dir.is_dir():
        raise PapiKidsRestoreDrillError("Dossier temporaire de restauration absent.")
    executable = shutil.which(pg_restore_binary)
    if not executable:
        raise PapiKidsRestoreDrillError("Binaire pg_restore introuvable.")
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        **target_env,
        "PGAPPNAME": "papi-kids-restore-drill",
    }
    with tempfile.TemporaryDirectory(prefix=".papi-restore-drill-", dir=target_dir) as temporary:
        os.chmod(temporary, 0o700)
        archive = Path(temporary) / "restore.pgdump"
        try:
            decrypt_and_verify_pg_dump_archive(
                backup_path, manifest_path, archive, key_env=key_env
            )
        except PapiKidsBackupError as exc:
            raise PapiKidsRestoreDrillError("La sauvegarde n'a pas passé la vérification cryptographique.") from exc
        command = [
            executable, "--no-password", "--clean", "--if-exists",
            "--no-owner", "--no-acl", "--exit-on-error",
            "--single-transaction", str(archive),
        ]
        try:
            result = subprocess.run(
                command, env=environment, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=timeout_seconds, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise PapiKidsRestoreDrillError("Le test de restauration a dépassé le délai.") from exc
        except OSError as exc:
            raise PapiKidsRestoreDrillError("Impossible de lancer pg_restore.") from exc
        if result.returncode != 0:
            raise PapiKidsRestoreDrillError(
                f"pg_restore a échoué (code {result.returncode}); détails sensibles masqués."
            )
    return {
        "status": "restore_drill_succeeded",
        "target_database": target_name,
        "target_isolated_by_name": True,
        "production_database_modified": False,
        "backup_authentication_verified": True,
        "restore_performed": True,
        "production_restore_performed": False,
    }
