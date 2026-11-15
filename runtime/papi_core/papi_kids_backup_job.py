"""Create an encrypted PostgreSQL backup without exposing credentials in argv."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

from .papi_kids_backup import encrypt_pg_dump_archive, PapiKidsBackupError


class PapiKidsBackupJobError(ValueError):
    """Database backup could not be created safely."""


def _database_environment(database_url: str) -> dict[str, str]:
    try:
        parsed = urlsplit(database_url)
        query = parse_qs(parsed.query)
        ssl_modes = query.get("sslmode", [])
        if parsed.scheme not in {"postgres", "postgresql"}:
            raise ValueError("scheme")
        if not parsed.hostname or not parsed.path.strip("/") or not parsed.username:
            raise ValueError("components")
        if ssl_modes != ["require"] and ssl_modes != ["verify-ca"] and ssl_modes != ["verify-full"]:
            raise ValueError("tls")
        port = parsed.port or 5432
        if not 1 <= port <= 65535:
            raise ValueError("port")
        password = unquote(parsed.password or "")
        if not password:
            raise ValueError("password")
        return {
            "PGHOST": parsed.hostname,
            "PGPORT": str(port),
            "PGDATABASE": unquote(parsed.path.lstrip("/")),
            "PGUSER": unquote(parsed.username),
            "PGPASSWORD": password,
            "PGSSLMODE": ssl_modes[0],
            "PGCONNECT_TIMEOUT": "10",
            "PGPASSFILE": os.devnull,
            "PGAPPNAME": "papi-kids-backup",
        }
    except Exception as exc:
        raise PapiKidsBackupJobError(
            "URL PostgreSQL invalide : hôte, base, utilisateur, mot de passe et TLS requis."
        ) from exc


def create_encrypted_postgres_backup(
    backup_dir: str | Path,
    *,
    database_url_env: str = "PAPI_KIDS_DATABASE_URL",
    key_env: str = "PAPI_KIDS_BACKUP_KEY_B64",
    key_id: str,
    pg_dump_binary: str = "pg_dump",
    timeout_seconds: int = 3600,
) -> dict[str, Any]:
    """Run pg_dump custom format, encrypt it, then delete the plaintext staging archive."""
    database_url = os.environ.get(database_url_env, "")
    if not database_url:
        raise PapiKidsBackupJobError("Secret de connexion PostgreSQL absent.")
    connection_env = _database_environment(database_url)
    target_dir = Path(backup_dir).resolve()
    if not target_dir.is_dir():
        raise PapiKidsBackupJobError("Dossier de sauvegarde hors site ou monté absent.")
    if not isinstance(timeout_seconds, int) or not 30 <= timeout_seconds <= 86400:
        raise PapiKidsBackupJobError("Délai de sauvegarde hors limites.")
    executable = shutil.which(pg_dump_binary)
    if not executable:
        raise PapiKidsBackupJobError("Binaire pg_dump introuvable sur le runner de sauvegarde.")

    with tempfile.TemporaryDirectory(prefix=".papi-pg-dump-", dir=target_dir) as staging:
        archive = Path(staging) / "database.pgdump"
        os.chmod(staging, 0o700)
        command = [
            executable, "--no-password", "--format=custom",
            "--no-owner", "--no-acl", "--file", str(archive),
        ]
        environment = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            **connection_env,
        }
        try:
            completed = subprocess.run(
                command, env=environment, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=timeout_seconds, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise PapiKidsBackupJobError("pg_dump a dépassé le délai autorisé.") from exc
        except OSError as exc:
            raise PapiKidsBackupJobError("Impossible de lancer pg_dump.") from exc
        if completed.returncode != 0:
            raise PapiKidsBackupJobError(
                f"pg_dump a échoué (code {completed.returncode}); détails sensibles masqués."
            )
        if not archive.is_file() or archive.stat().st_size < 5:
            raise PapiKidsBackupJobError("pg_dump n'a produit aucune archive exploitable.")
        try:
            encrypted = encrypt_pg_dump_archive(
                archive, target_dir, key_env=key_env, key_id=key_id
            )
        except PapiKidsBackupError as exc:
            raise PapiKidsBackupJobError("Le chiffrement de la sauvegarde a échoué.") from exc
        return {
            **encrypted,
            "database_dump_created": True,
            "plaintext_staging_deleted": True,
            "database_url_exposed_in_argv": False,
            "password_exposed_in_argv": False,
            "offsite_upload_performed": False,
        }
