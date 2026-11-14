"""Offline Supabase deployment preflight; never contacts a hosted project."""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse


class SupabasePreflightError(ValueError):
    """Repository migration inventory or local configuration is unsafe."""


MIGRATION_NAME = re.compile(r"^(\d{3})_([a-z0-9_]+)\.sql$")
SECRET_FILE_EXCEPTIONS = {".env.example", ".env.sample"}


def _migration_inventory(root: Path) -> list[dict[str, object]]:
    directory = root / "infra" / "supabase" / "migrations"
    if not directory.is_dir():
        raise SupabasePreflightError("Répertoire des migrations Supabase absent.")
    entries: dict[int, Path] = {}
    for path in sorted(directory.glob("*.sql")):
        if path.name.endswith("_down.sql"):
            continue
        match = MIGRATION_NAME.fullmatch(path.name)
        if not match:
            raise SupabasePreflightError(f"Nom de migration non conforme : {path.name}")
        version = int(match.group(1))
        if version in entries:
            raise SupabasePreflightError(f"Version de migration dupliquée : {version:03d}")
        entries[version] = path
    if not entries:
        raise SupabasePreflightError("Aucune migration ascendante trouvée.")
    versions = sorted(entries)
    expected = list(range(versions[0], versions[-1] + 1))
    if versions != expected:
        missing = sorted(set(expected) - set(versions))
        raise SupabasePreflightError(
            "Séquence de migrations discontinue : " + ", ".join(f"{item:03d}" for item in missing)
        )
    inventory = []
    for version, path in sorted(entries.items()):
        rollback = path.with_name(path.stem + "_down.sql")
        raw = path.read_bytes()
        inventory.append({
            "version": f"{version:03d}",
            "filename": path.name,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "rollback_available": rollback.is_file(),
        })
    return inventory


def _validate_url(raw_url: str) -> bool:
    parsed = urlparse(raw_url)
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and parsed.hostname.endswith(".supabase.co")
        and parsed.username is None
        and parsed.password is None
        and parsed.port is None
        and parsed.path in ("", "/")
        and not parsed.query
        and not parsed.fragment
    )


def _find_env_files(root: Path) -> list[str]:
    found = []
    for path in root.rglob(".env*"):
        if not path.is_file() or path.name in SECRET_FILE_EXCEPTIONS:
            continue
        if any(part in {".git", ".venv", "venv", "__pycache__", "node_modules"} for part in path.parts):
            continue
        found.append(path.relative_to(root).as_posix())
    return sorted(found)


def run_supabase_preflight(
    root: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Validate local deployment inputs without network access or secret disclosure."""
    repository = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    env = os.environ if environ is None else environ
    schema = repository / "infra" / "supabase" / "schema.sql"
    if not schema.is_file() or not schema.read_text(encoding="utf-8").strip():
        raise SupabasePreflightError("Schéma Supabase absent ou vide.")

    url = env.get("SUPABASE_URL", "").strip()
    key_name = (
        "SUPABASE_SERVICE_ROLE_KEY" if env.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        else "SUPABASE_KEY" if env.get("SUPABASE_KEY", "").strip()
        else None
    )
    url_valid = _validate_url(url) if url else False
    env_files = _find_env_files(repository)
    migrations = _migration_inventory(repository)
    latest = migrations[-1]
    configured = bool(url_valid and key_name)
    return {
        "status": "ready_for_operator_review" if configured and not env_files else (
            "blocked_unsafe_env_files" if env_files else "blocked_missing_or_invalid_configuration"
        ),
        "repository_schema_present": True,
        "migration_count": len(migrations),
        "first_migration": migrations[0]["version"],
        "latest_migration": latest["version"],
        "migrations": migrations,
        "supabase_url_configured": bool(url),
        "supabase_url_valid": url_valid,
        "server_key_configured": key_name is not None,
        "server_key_variable": key_name,
        "environment_files_found": env_files,
        "network_access_performed": False,
        "remote_migrations_applied": False,
        "deployment_performed": False,
        "remote_changes_permitted": False,
        "production_readiness_proven": False,
    }


def require_supabase_configuration(report: dict[str, object]) -> None:
    """Fail closed when an operator explicitly requires configured local inputs."""
    if report["status"] != "ready_for_operator_review":
        raise SupabasePreflightError(
            "Préparation Supabase bloquée : vérifier URL HTTPS, clé serveur et absence de fichiers .env."
        )
