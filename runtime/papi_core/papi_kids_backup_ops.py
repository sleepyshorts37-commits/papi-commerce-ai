"""Non-destructive retention planner and backup health assessment."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import re
import json
from pathlib import Path
from typing import Any

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class PapiKidsBackupOpsError(ValueError):
    """Invalid backup inventory or retention policy."""


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise PapiKidsBackupOpsError("Horodatage de sauvegarde invalide.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PapiKidsBackupOpsError("Horodatage de sauvegarde invalide.") from exc
    if parsed.tzinfo is None:
        raise PapiKidsBackupOpsError("Les horodatages doivent inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)


def plan_backup_retention(
    backups: list[dict[str, Any]],
    *,
    now: datetime | None = None,
    keep_daily: int = 7,
    keep_weekly: int = 4,
    keep_monthly: int = 12,
) -> dict[str, Any]:
    """Return keep/delete candidates only; this function never deletes any file."""
    if not isinstance(backups, list):
        raise PapiKidsBackupOpsError("Inventaire de sauvegardes invalide.")
    if any(not isinstance(n, int) or isinstance(n, bool) or n < 1 or n > 3650
           for n in (keep_daily, keep_weekly, keep_monthly)):
        raise PapiKidsBackupOpsError("Politique de rétention hors limites.")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise PapiKidsBackupOpsError("L'heure de référence doit être timezone-aware.")
    current = current.astimezone(timezone.utc)

    normalized = []
    seen = set()
    for item in backups:
        if not isinstance(item, dict):
            raise PapiKidsBackupOpsError("Entrée de sauvegarde invalide.")
        backup_id = item.get("backup_file")
        digest = item.get("encrypted_sha256")
        if not isinstance(backup_id, str) or not backup_id or backup_id in seen:
            raise PapiKidsBackupOpsError("Nom de sauvegarde absent ou dupliqué.")
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise PapiKidsBackupOpsError(f"Empreinte invalide pour {backup_id}.")
        seen.add(backup_id)
        created = _timestamp(item.get("created_at"))
        if created > current + timedelta(minutes=5):
            raise PapiKidsBackupOpsError(f"Horodatage futur pour {backup_id}.")
        normalized.append((created, backup_id, item))

    normalized.sort(reverse=True)
    keep: set[str] = set()
    daily = {}
    weekly = {}
    monthly = {}
    for created, backup_id, _ in normalized:
        day_key = created.date()
        week_key = created.isocalendar()[:2]
        month_key = (created.year, created.month)
        daily.setdefault(day_key, backup_id)
        weekly.setdefault(week_key, backup_id)
        monthly.setdefault(month_key, backup_id)
    keep.update(list(daily.values())[:keep_daily])
    keep.update(list(weekly.values())[:keep_weekly])
    keep.update(list(monthly.values())[:keep_monthly])

    retained = []
    deletion_candidates = []
    for created, backup_id, item in normalized:
        record = {
            "backup_file": backup_id,
            "created_at": created.isoformat(),
            "encrypted_sha256": item["encrypted_sha256"],
            "offsite_copy_verified": item.get("offsite_copy_verified") is True,
        }
        (retained if backup_id in keep else deletion_candidates).append(record)
    return {
        "policy": {
            "keep_daily": keep_daily,
            "keep_weekly": keep_weekly,
            "keep_monthly": keep_monthly,
        },
        "retained": retained,
        "deletion_candidates": deletion_candidates,
        "deletion_performed": False,
        "human_approval_required_before_deletion": True,
    }


def evaluate_backup_health(
    backups: list[dict[str, Any]],
    *,
    last_restore_drill_at: str | None,
    now: datetime | None = None,
    max_backup_age_hours: int = 24,
    max_restore_drill_age_days: int = 30,
) -> dict[str, Any]:
    """Assess freshness, offsite evidence and restore-test recency."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise PapiKidsBackupOpsError("L'heure de référence doit être timezone-aware.")
    current = current.astimezone(timezone.utc)
    if not isinstance(backups, list) or not backups:
        return {
            "status": "unhealthy",
            "blockers": ["Aucune sauvegarde chiffrée enregistrée."],
            "backup_fresh": False,
            "offsite_verified": False,
            "restore_drill_fresh": False,
        }
    parsed = [(_timestamp(item.get("created_at")), item) for item in backups if isinstance(item, dict)]
    if len(parsed) != len(backups):
        raise PapiKidsBackupOpsError("Inventaire de sauvegardes invalide.")
    newest_time, newest = max(parsed, key=lambda pair: pair[0])
    age = current - newest_time
    backup_fresh = timedelta(0) <= age <= timedelta(hours=max_backup_age_hours)
    offsite_verified = newest.get("offsite_copy_verified") is True and bool(newest.get("offsite_evidence_ref"))
    try:
        restore_time = _timestamp(last_restore_drill_at) if last_restore_drill_at else None
    except PapiKidsBackupOpsError:
        restore_time = None
    restore_fresh = (
        restore_time is not None
        and timedelta(0) <= current - restore_time <= timedelta(days=max_restore_drill_age_days)
    )
    blockers = []
    if not backup_fresh:
        blockers.append("La dernière sauvegarde dépasse le délai de fraîcheur autorisé ou date du futur.")
    if not offsite_verified:
        blockers.append("Copie hors site non vérifiée ou preuve absente.")
    if not restore_fresh:
        blockers.append("Aucun test de restauration réussi dans la période autorisée.")
    return {
        "status": "healthy" if not blockers else "unhealthy",
        "blockers": blockers,
        "latest_backup_file": newest.get("backup_file"),
        "latest_backup_age_hours": round(age.total_seconds() / 3600, 2),
        "backup_fresh": backup_fresh,
        "offsite_verified": offsite_verified,
        "restore_drill_fresh": restore_fresh,
        "destructive_actions_performed": False,
    }


def load_backup_health_inventory(backup_dir: str | Path) -> list[dict[str, Any]]:
    """Load local backup manifests and attach only matching offsite verification evidence."""
    directory = Path(backup_dir).resolve()
    if not directory.is_dir():
        raise PapiKidsBackupOpsError("Dossier de sauvegarde introuvable.")
    verification_path = directory / "offsite-verification.json"
    verification = {}
    if verification_path.is_file():
        try:
            document = json.loads(verification_path.read_text(encoding="utf-8"))
            if document.get("status") == "offsite_copy_verified" and document.get("checksum_verified") is True:
                verification = {
                    item.get("backup_file"): item
                    for item in document.get("backups", [])
                    if isinstance(item, dict)
                }
        except Exception:
            verification = {}
    inventory = []
    for encrypted in sorted(directory.glob("*.pgdump.aesgcm")):
        manifest_path = Path(str(encrypted) + ".json")
        if not manifest_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise PapiKidsBackupOpsError("Manifeste de sauvegarde illisible.") from exc
        if manifest.get("backup_file") != encrypted.name or manifest.get("encrypted") is not True:
            raise PapiKidsBackupOpsError("Manifeste non lié à la sauvegarde.")
        digest_builder = hashlib.sha256()
        with encrypted.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest_builder.update(chunk)
        digest = digest_builder.hexdigest()
        if digest != manifest.get("encrypted_sha256"):
            raise PapiKidsBackupOpsError("SHA-256 local incorrect.")
        proof = verification.get(encrypted.name, {})
        verified = (
            proof.get("offsite_copy_verified") is True
            and proof.get("encrypted_sha256") == digest
            and isinstance(proof.get("offsite_evidence_ref"), str)
            and bool(proof.get("offsite_evidence_ref"))
        )
        inventory.append({
            "backup_file": encrypted.name,
            "created_at": manifest.get("created_at"),
            "encrypted_sha256": digest,
            "offsite_copy_verified": verified,
            "offsite_evidence_ref": proof.get("offsite_evidence_ref") if verified else None,
        })
    return inventory
