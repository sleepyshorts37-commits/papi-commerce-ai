"""Read-only operational readiness diagnostics; never returns secret values."""
from __future__ import annotations

import os
from pathlib import Path
import stat
from typing import Any, Callable


REQUIRED_TABLES = {
    "books",
    "editorial_jobs",
    "manuscript_safety_reviews",
    "kdp_listing_metadata_versions",
    "kdp_package_builds",
    "kdp_package_reviews",
    "kindle_previewer_reviews",
}


def _secret_present(name: str, minimum: int = 32) -> bool:
    value = os.environ.get(name, "")
    return isinstance(value, str) and len(value) >= minimum


def check_papi_kids_readiness(
    *,
    storage_root: str | Path,
    connection_factory: Callable[[], Any],
) -> dict[str, Any]:
    """Report deployment readiness without exposing credentials or making provider calls."""
    checks: dict[str, Any] = {}
    blockers: list[str] = []

    root = Path(storage_root).resolve()
    storage_ok = root.is_dir() and os.access(root, os.R_OK | os.W_OK | os.X_OK)
    storage_mode = stat.S_IMODE(root.stat().st_mode) if root.exists() else None
    storage_private = storage_mode is not None and storage_mode & 0o077 == 0
    checks["private_storage"] = {
        "configured": storage_ok,
        "private_permissions": storage_private,
        "permissions_octal": oct(storage_mode) if storage_mode is not None else None,
    }
    if not storage_ok:
        blockers.append("Stockage privé absent ou non accessible.")
    elif not storage_private:
        blockers.append("Le stockage privé doit être accessible uniquement au compte serveur (mode 0700).")

    core_missing = []
    if not os.environ.get("SUPABASE_URL", "").startswith("https://"):
        core_missing.append("SUPABASE_URL")
    for name in ("SUPABASE_SERVICE_ROLE_KEY", "PAPI_KIDS_UPLOAD_TOKEN"):
        if not _secret_present(name):
            core_missing.append(name)
    checks["core_secrets"] = {
        "configured": not core_missing,
        "missing": core_missing,
        "values_exposed": False,
    }
    if core_missing:
        blockers.append("Secrets de base manquants ou trop courts.")

    workflow_env = (
        "PAPI_KIDS_REVIEW_TOKEN",
        "PAPI_KIDS_SAFETY_REVIEW_TOKEN",
        "PAPI_KIDS_METADATA_TOKEN",
        "PAPI_KIDS_KDP_BUILD_TOKEN",
        "PAPI_KIDS_KDP_REVIEW_TOKEN",
        "PAPI_KIDS_KINDLE_PREVIEWER_TOKEN",
        "PAPI_KIDS_REVIEWER_ID",
        "PAPI_KIDS_METADATA_EDITOR_ID",
    )
    workflow_missing = [name for name in workflow_env if not _secret_present(name, 3 if name.endswith("_ID") else 32)]
    checks["owner_workflow_secrets"] = {
        "configured": not workflow_missing,
        "missing": workflow_missing,
        "values_exposed": False,
    }
    if workflow_missing:
        blockers.append("Un ou plusieurs jetons ou identifiants des workflows propriétaire manquent.")

    provider_env = ("CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN")
    provider_missing = [name for name in provider_env if not _secret_present(name)]
    checks["image_provider"] = {
        "configured": not provider_missing,
        "missing": provider_missing,
        "external_probe_performed": False,
        "quota_verified": False,
    }

    build_enabled = os.environ.get("PAPI_KIDS_KDP_BUILD_ENABLED", "false").lower() == "true"
    checks["kdp_package_build"] = {
        "enabled": build_enabled,
        "token_configured": _secret_present("PAPI_KIDS_KDP_BUILD_TOKEN"),
        "private_profile_required_per_book": True,
    }

    database_ok = False
    missing_tables = sorted(REQUIRED_TABLES)
    connection = None
    try:
        connection = connection_factory()
        cursor = connection.cursor()
        cursor.execute("select 1")
        database_ok = cursor.fetchone() is not None
        cursor.execute(
            """select table_name from information_schema.tables
                where table_schema = 'papi_kids_private'
                  and table_name = any(%s)""",
            (sorted(REQUIRED_TABLES),),
        )
        existing = {row[0] for row in cursor.fetchall()}
        missing_tables = sorted(REQUIRED_TABLES - existing)
    except Exception:
        database_ok = False
    finally:
        if connection is not None:
            close = getattr(connection, "close", None)
            if callable(close):
                close()
    checks["database"] = {
        "connected": database_ok,
        "missing_required_tables": missing_tables if database_ok else sorted(REQUIRED_TABLES),
    }
    if not database_ok:
        blockers.append("Connexion PostgreSQL/Supabase impossible.")
    elif missing_tables:
        blockers.append("Migrations PAPI KIDS incomplètes.")

    core_ready = storage_ok and storage_private and not core_missing and database_ok and not missing_tables
    owner_ready = not workflow_missing
    return {
        "status": "ready_for_owner_configuration" if core_ready and owner_ready else "blocked",
        "core_ready": core_ready,
        "owner_workflows_ready": owner_ready,
        "image_generation_ready": core_ready and not provider_missing,
        "package_build_enabled": build_enabled and _secret_present("PAPI_KIDS_KDP_BUILD_TOKEN"),
        "checks": checks,
        "blockers": blockers,
        "external_provider_calls": False,
        "spend_limit_minor": 0,
        "secrets_returned": False,
        "publication_performed": False,
    }
