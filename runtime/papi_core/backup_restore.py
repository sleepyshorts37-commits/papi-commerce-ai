"""Validation hors-ligne de manifestes de sauvegarde et plans de restauration.

Aucune lecture/écriture disque, connexion distante ou restauration réelle n'est effectuée.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class BackupValidationError(ValueError):
    """Manifeste ou contenu de sauvegarde invalide."""


def _utc_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise BackupValidationError("created_at doit être une date ISO-8601.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BackupValidationError("created_at invalide.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise BackupValidationError("created_at doit être explicitement en UTC.")
    return parsed


def _safe_relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 240:
        raise BackupValidationError("Chemin d'artefact invalide.")
    if value.startswith("/") or "\\\\" in value or ":" in value:
        raise BackupValidationError("Le chemin doit être relatif et portable.")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise BackupValidationError("Le chemin contient un segment interdit.")
    return value


def validate_backup_manifest(
    manifest: dict[str, Any], payloads: dict[str, bytes]
) -> dict[str, Any]:
    """Vérifie intégrité, complétude et cohérence sans restaurer les artefacts."""
    if not isinstance(manifest, dict) or not isinstance(payloads, dict):
        raise BackupValidationError("Manifeste et payloads doivent être des objets.")
    backup_id = manifest.get("backup_id")
    source = manifest.get("source")
    schema_version = manifest.get("schema_version")
    if not isinstance(backup_id, str) or not backup_id.strip() or len(backup_id) > 100:
        raise BackupValidationError("backup_id invalide.")
    if not isinstance(source, str) or not source.strip() or len(source) > 200:
        raise BackupValidationError("source invalide.")
    if not isinstance(schema_version, str) or not schema_version.strip():
        raise BackupValidationError("schema_version manquante.")
    _utc_timestamp(manifest.get("created_at"))
    retention = manifest.get("retention_days")
    if isinstance(retention, bool) or not isinstance(retention, int) or not 1 <= retention <= 3650:
        raise BackupValidationError("retention_days doit être compris entre 1 et 3650.")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise BackupValidationError("Au moins un artefact est requis.")

    seen: set[str] = set()
    verified: list[str] = []
    for item in artifacts:
        if not isinstance(item, dict):
            raise BackupValidationError("Chaque artefact doit être un objet.")
        path = _safe_relative_path(item.get("path"))
        if path in seen:
            raise BackupValidationError("Chemin d'artefact dupliqué.")
        seen.add(path)
        digest = item.get("sha256")
        size = item.get("size_bytes")
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise BackupValidationError("Empreinte SHA-256 invalide.")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise BackupValidationError("size_bytes invalide.")
        if not isinstance(item.get("kind"), str) or not item["kind"].strip():
            raise BackupValidationError("kind d'artefact manquant.")
        content = payloads.get(path)
        if not isinstance(content, bytes):
            raise BackupValidationError("Contenu d'artefact absent ou invalide.")
        if len(content) != size or hashlib.sha256(content).hexdigest() != digest:
            raise BackupValidationError("Échec de vérification d'intégrité.")
        verified.append(path)

    if set(payloads) != seen:
        raise BackupValidationError("Le jeu de payloads diffère du manifeste.")
    return {
        "status": "verified",
        "backup_id": backup_id,
        "artifact_count": len(verified),
        "verified_paths": verified,
        "restore_performed": False,
        "remote_storage_accessed": False,
    }


def build_restore_plan(
    manifest: dict[str, Any], payloads: dict[str, bytes], *, target_environment: str
) -> dict[str, Any]:
    """Construit un plan descriptif après vérification ; n'écrit aucune donnée."""
    if not isinstance(target_environment, str) or not target_environment.strip():
        raise BackupValidationError("target_environment doit être renseigné.")
    verification = validate_backup_manifest(manifest, payloads)
    return {
        "status": "ready_for_human_review",
        "backup_id": verification["backup_id"],
        "target_environment": target_environment,
        "ordered_paths": verification["verified_paths"],
        "human_approval_required": True,
        "writes_performed": False,
        "restore_performed": False,
    }
