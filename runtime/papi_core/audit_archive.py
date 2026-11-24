"""Archives locales vérifiables du journal d'audit, sans rotation ni suppression.

Chaque archive contient une copie complète du journal et un manifeste lié à un
checkpoint d'ancrage déjà vérifié. La source n'est jamais tronquée ni supprimée.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .anchor import AnchorClient, AnchorError, CHECKPOINT_ID_RE
from .audit import AuditError, MAX_AUDIT_EVENTS, MAX_JOURNAL_BYTES, read_events

ARCHIVE_VERSION = 1
MANIFEST_NAME = "manifest.json"
JOURNAL_NAME = "journal.jsonl"
MAX_MANIFEST_BYTES = 16 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MANIFEST_FIELDS = {
    "version", "archive_id", "created_at", "journal_sha256",
    "journal_size_bytes", "event_count", "first_event_hash", "last_event_hash",
    "checkpoint_id", "checkpoint_digest", "checkpoint_sequence",
}


class AuditArchiveError(ValueError):
    """Archive absente, invalide, non privée ou non liée à un checkpoint fiable."""


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AuditArchiveError("Clé JSON dupliquée dans le manifeste.")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise AuditArchiveError(f"Constante JSON non standard interdite : {value}")


def _canonical_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.isoformat(timespec="seconds").replace("+00:00", "Z") == value


def _check_parent_components(path: Path) -> None:
    """Refuse les composants parents symboliques pour éviter les redirections."""
    parent = path.parent
    for component in reversed(parent.parents):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise AuditArchiveError("Un répertoire parent est symbolique ou invalide.")
    info = parent.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise AuditArchiveError("Le répertoire parent doit être un dossier réel existant.")


def _check_private_directory(path: Path) -> None:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise AuditArchiveError("Le dossier d'archive doit être un dossier réel.")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise AuditArchiveError("Le dossier d'archive doit être privé (0700).")
    if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
        raise AuditArchiveError("Le dossier d'archive doit appartenir au processus courant.")


def _read_private_file(path: Path, maximum: int) -> bytes:
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise AuditArchiveError("La plateforme ne permet pas de refuser les liens symboliques.")
    try:
        descriptor = os.open(path, os.O_RDONLY | nofollow | getattr(os, "O_NONBLOCK", 0))
    except OSError as exc:
        raise AuditArchiveError("Fichier d'archive absent ou inaccessible.") from exc
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise AuditArchiveError("Les fichiers d'archive doivent être réguliers.")
        if stat.S_IMODE(info.st_mode) & 0o077:
            raise AuditArchiveError("Les fichiers d'archive doivent être privés (0600).")
        if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
            raise AuditArchiveError("Les fichiers d'archive doivent appartenir au processus courant.")
        if info.st_size > maximum:
            raise AuditArchiveError("Fichier d'archive trop volumineux.")
        raw = stream.read(maximum + 1)
        if len(raw) > maximum or os.fstat(stream.fileno()).st_size != len(raw):
            raise AuditArchiveError("Fichier modifié pendant sa lecture ou limite dépassée.")
        return raw


def _write_new_private_file(path: Path, payload: bytes) -> None:
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise AuditArchiveError("La plateforme ne permet pas de refuser les liens symboliques.")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow
    descriptor = os.open(path, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        view = memoryview(payload)
        written = 0
        while written < len(view):
            count = os.write(descriptor, view[written:])
            if count <= 0:
                raise OSError("Écriture d'archive interrompue.")
            written += count
        os.fsync(descriptor)
    except BaseException:
        os.close(descriptor)
        try:
            path.unlink()
        except OSError:
            pass
        raise
    else:
        os.close(descriptor)


def _verify_journal_bytes(raw: bytes) -> list[dict[str, Any]]:
    if not raw or len(raw) > MAX_JOURNAL_BYTES:
        raise AuditArchiveError("Le journal archivé est vide ou dépasse la limite autorisée.")
    with tempfile.TemporaryDirectory(prefix="papi-audit-verify-") as directory:
        temporary_path = Path(directory) / JOURNAL_NAME
        _write_new_private_file(temporary_path, raw)
        try:
            events = read_events(temporary_path)
        except AuditError as exc:
            raise AuditArchiveError("La copie du journal ne passe pas la vérification cryptographique.") from exc
        return events


def _verified_anchor(
    client: AnchorClient, checkpoint_id: str, *, require_head: bool
) -> dict[str, Any]:
    try:
        chain = client.verify_chain()
    except AnchorError:
        raise
    if not chain:
        raise AuditArchiveError("Aucun checkpoint d'ancrage vérifié.")
    if require_head and chain[-1]["checkpoint_id"] != checkpoint_id:
        raise AuditArchiveError("La création exige le checkpoint courant comme tête d'ancrage.")
    checkpoint = next((item for item in chain if item["checkpoint_id"] == checkpoint_id), None)
    if checkpoint is None:
        raise AuditArchiveError("Le checkpoint indiqué n'appartient pas à la chaîne vérifiée.")
    return checkpoint


def _validate_manifest(raw: bytes) -> dict[str, Any]:
    try:
        manifest = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, AuditArchiveError) as exc:
        raise AuditArchiveError("Manifeste JSON invalide.") from exc
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_FIELDS:
        raise AuditArchiveError("Structure de manifeste invalide.")
    try:
        if raw != _canonical(manifest):
            raise AuditArchiveError("Le manifeste n'est pas encodé de manière canonique.")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise AuditArchiveError("Le manifeste contient une valeur non canonique.") from exc
    if isinstance(manifest["version"], bool) or manifest["version"] != ARCHIVE_VERSION:
        raise AuditArchiveError("Version d'archive inconnue.")
    try:
        parsed_id = str(uuid.UUID(manifest["archive_id"]))
    except (ValueError, TypeError, AttributeError) as exc:
        raise AuditArchiveError("Identifiant d'archive invalide.") from exc
    if parsed_id != manifest["archive_id"]:
        raise AuditArchiveError("Identifiant d'archive non canonique.")
    if not _canonical_timestamp(manifest["created_at"]):
        raise AuditArchiveError("created_at doit être un horodatage UTC canonique.")
    for field in ("journal_sha256", "first_event_hash", "last_event_hash", "checkpoint_digest"):
        if not isinstance(manifest[field], str) or not SHA256_RE.fullmatch(manifest[field]):
            raise AuditArchiveError(f"{field} doit être un SHA-256.")
    if not isinstance(manifest["checkpoint_id"], str) or not CHECKPOINT_ID_RE.fullmatch(manifest["checkpoint_id"]):
        raise AuditArchiveError("checkpoint_id invalide.")
    for field, maximum in (("journal_size_bytes", MAX_JOURNAL_BYTES), ("event_count", MAX_AUDIT_EVENTS), ("checkpoint_sequence", MAX_AUDIT_EVENTS)):
        value = manifest[field]
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
            raise AuditArchiveError(f"{field} est hors limites.")
    return manifest


def _load_verified_archive(
    archive_directory: str | Path, anchor_client: AnchorClient
) -> tuple[dict[str, Any], bytes, list[dict[str, Any]]]:
    directory = Path(archive_directory)
    _check_private_directory(directory)
    if set(os.listdir(directory)) != {MANIFEST_NAME, JOURNAL_NAME}:
        raise AuditArchiveError("L'archive doit contenir exactement le manifeste et le journal.")
    manifest = _validate_manifest(_read_private_file(directory / MANIFEST_NAME, MAX_MANIFEST_BYTES))
    raw = _read_private_file(directory / JOURNAL_NAME, MAX_JOURNAL_BYTES)
    if len(raw) != manifest["journal_size_bytes"]:
        raise AuditArchiveError("La taille du journal ne correspond pas au manifeste.")
    if not hashlib.sha256(raw).hexdigest() == manifest["journal_sha256"]:
        raise AuditArchiveError("L'empreinte du journal ne correspond pas au manifeste.")
    events = _verify_journal_bytes(raw)
    if (
        len(events) != manifest["event_count"]
        or events[0]["event_hash"] != manifest["first_event_hash"]
        or events[-1]["event_hash"] != manifest["last_event_hash"]
    ):
        raise AuditArchiveError("Les événements ne correspondent pas au manifeste.")
    checkpoint = _verified_anchor(anchor_client, manifest["checkpoint_id"], require_head=False)
    if (
        checkpoint["digest"] != manifest["checkpoint_digest"]
        or checkpoint["sequence"] != manifest["checkpoint_sequence"]
        or checkpoint["sequence"] != len(events)
        or checkpoint["audit_head"] != events[-1]["event_hash"]
    ):
        raise AuditArchiveError("L'archive ne correspond pas au checkpoint d'audit vérifié.")
    return manifest, raw, events


def verify_archive(
    archive_directory: str | Path, anchor_client: AnchorClient
) -> dict[str, Any]:
    """Vérifie le manifeste, les octets, toute la chaîne JSONL et le checkpoint."""
    manifest, _raw, events = _load_verified_archive(archive_directory, anchor_client)
    return {
        "archive_id": manifest["archive_id"],
        "event_count": len(events),
        "journal_sha256": manifest["journal_sha256"],
        "last_event_hash": events[-1]["event_hash"],
        "checkpoint_id": manifest["checkpoint_id"],
        "verified": True,
    }


def create_verified_archive(
    journal_path: str | Path,
    archive_directory: str | Path,
    anchor_client: AnchorClient,
) -> dict[str, Any]:
    """Crée une copie complète liée à la tête d'ancrage actuelle, sans toucher à la source."""
    source = Path(journal_path)
    destination = Path(archive_directory)
    _check_parent_components(destination)
    if destination.exists() or destination.is_symlink():
        raise AuditArchiveError("Le dossier d'archive existe déjà; aucun écrasement n'est autorisé.")
    try:
        events_before = read_events(source)
        raw = _read_private_file(source, MAX_JOURNAL_BYTES)
    except (AuditError, AuditArchiveError) as exc:
        raise AuditArchiveError("Le journal source ne peut pas être archivé en toute sécurité.") from exc
    events = _verify_journal_bytes(raw)
    if events != events_before or not events:
        raise AuditArchiveError("Le journal a changé ou est vide pendant la préparation de l'archive.")
    checkpoint = _verified_anchor(
        anchor_client, anchor_client.verify_chain()[-1]["checkpoint_id"], require_head=True
    )
    if checkpoint["sequence"] != len(events) or checkpoint["audit_head"] != events[-1]["event_hash"]:
        raise AuditArchiveError("Un checkpoint actuel correspondant exactement au journal est requis.")

    manifest = {
        "version": ARCHIVE_VERSION,
        "archive_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "journal_sha256": hashlib.sha256(raw).hexdigest(),
        "journal_size_bytes": len(raw),
        "event_count": len(events),
        "first_event_hash": events[0]["event_hash"],
        "last_event_hash": events[-1]["event_hash"],
        "checkpoint_id": checkpoint["checkpoint_id"],
        "checkpoint_digest": checkpoint["digest"],
        "checkpoint_sequence": checkpoint["sequence"],
    }
    manifest_bytes = _canonical(manifest)
    os.mkdir(destination, 0o700)
    created: list[Path] = []
    try:
        _write_new_private_file(destination / JOURNAL_NAME, raw)
        created.append(destination / JOURNAL_NAME)
        _write_new_private_file(destination / MANIFEST_NAME, manifest_bytes)
        created.append(destination / MANIFEST_NAME)
        directory_fd = os.open(destination, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return verify_archive(destination, anchor_client)
    except BaseException:
        for path in created:
            try:
                path.unlink()
            except OSError:
                pass
        try:
            destination.rmdir()
        except OSError:
            pass
        raise


def restore_verified_archive(
    archive_directory: str | Path,
    destination_journal: str | Path,
    anchor_client: AnchorClient,
) -> dict[str, Any]:
    """Restaure uniquement vers un chemin absent, après vérification complète."""
    _check_parent_components(Path(destination_journal))
    _manifest, raw, events = _load_verified_archive(archive_directory, anchor_client)
    destination = Path(destination_journal)
    try:
        _write_new_private_file(destination, raw)
        restored = read_events(destination)
        if restored != events:
            raise AuditArchiveError("Le journal restauré ne correspond pas à l'archive.")
    except BaseException:
        try:
            destination.unlink()
        except OSError:
            pass
        raise
    return {
        "restored": True,
        "event_count": len(events),
        "last_event_hash": events[-1]["event_hash"],
    }
