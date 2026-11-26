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
    """Prépare, synchronise et ferme un fichier privé avant publication atomique."""
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
    except OSError as exc:
        raise AuditArchiveError("Impossible de préparer un fichier temporaire privé.") from exc
    temporary = Path(temporary_name)
    descriptor_open = True
    try:
        try:
            os.fchmod(descriptor, 0o600)
            view = memoryview(payload)
            written = 0
            while written < len(view):
                try:
                    count = os.write(descriptor, view[written:])
                except InterruptedError:
                    continue
                if count <= 0:
                    raise OSError("Écriture d'archive interrompue.")
                written += count
            os.fsync(descriptor)
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise AuditArchiveError("Le fichier temporaire d'archive n'est pas régulier.")
        except OSError as exc:
            raise AuditArchiveError("Écriture temporaire du fichier d'archive impossible.") from exc

        # Close before linking: a close failure must never leave a published target.
        descriptor_open = False
        try:
            os.close(descriptor)
        except OSError as exc:
            raise AuditArchiveError("Fermeture du fichier temporaire d'archive impossible.") from exc

        try:
            # A hard link publishes the complete fsynced inode atomically and
            # fails if the destination exists; unlike rename, it never replaces it.
            os.link(temporary, path)
        except FileExistsError:
            raise
        except OSError as exc:
            raise AuditArchiveError(
                "Publication atomique impossible sur ce système de fichiers."
            ) from exc
    finally:
        if descriptor_open:
            try:
                os.close(descriptor)
            except OSError:
                pass
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            # A leftover hidden temporary is rejected by exact archive verification.
            pass


def _fsync_directory(path: Path) -> None:
    """Synchronise les entrées du répertoire sans suivre de lien symbolique."""
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory_flag = getattr(os, "O_DIRECTORY", None)
    if nofollow is None or directory_flag is None:
        raise AuditArchiveError(
            "La plateforme ne permet pas d'ouvrir un répertoire sans suivre de lien symbolique."
        )
    try:
        descriptor = os.open(path, os.O_RDONLY | directory_flag | nofollow)
    except OSError as exc:
        raise AuditArchiveError("Impossible d'ouvrir le répertoire pour synchroniser l'archive.") from exc
    try:
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise AuditArchiveError("La synchronisation exige un véritable répertoire.")
        os.fsync(descriptor)
    except OSError as exc:
        raise AuditArchiveError("Impossible de garantir la durabilité des entrées du répertoire.") from exc
    finally:
        os.close(descriptor)


def _verify_journal_bytes(raw: bytes) -> list[dict[str, Any]]:
    if not raw or len(raw) > MAX_JOURNAL_BYTES:
        raise AuditArchiveError("Le journal archivé est vide ou dépasse la limite autorisée.")
    with tempfile.TemporaryDirectory(prefix="papi-audit-verify-") as directory:
        temporary_path = Path(directory) / JOURNAL_NAME
        _write_new_private_file(temporary_path, raw)
        try:
            return read_events(temporary_path)
        except (AuditError, OSError, RecursionError) as exc:
            raise AuditArchiveError("La copie du journal ne passe pas la vérification cryptographique.") from exc


def _verified_anchor(
    client: AnchorClient, checkpoint_id: str, *, require_head: bool
) -> dict[str, Any]:
    chain = client.verify_chain()
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
    except (UnicodeDecodeError, json.JSONDecodeError, AuditArchiveError, RecursionError) as exc:
        raise AuditArchiveError("Manifeste JSON invalide.") from exc
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_FIELDS:
        raise AuditArchiveError("Structure de manifeste invalide.")
    try:
        if raw != _canonical(manifest):
            raise AuditArchiveError("Le manifeste n'est pas encodé de manière canonique.")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise AuditArchiveError("Le manifeste contient une valeur non canonique.") from exc
    version = manifest["version"]
    if isinstance(version, bool) or not isinstance(version, int) or version != ARCHIVE_VERSION:
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
    _check_parent_components(directory)
    _check_private_directory(directory)
    if set(os.listdir(directory)) != {MANIFEST_NAME, JOURNAL_NAME}:
        raise AuditArchiveError("L'archive doit contenir exactement le manifeste et le journal.")
    manifest = _validate_manifest(_read_private_file(directory / MANIFEST_NAME, MAX_MANIFEST_BYTES))
    raw = _read_private_file(directory / JOURNAL_NAME, MAX_JOURNAL_BYTES)
    if len(raw) != manifest["journal_size_bytes"]:
        raise AuditArchiveError("La taille du journal ne correspond pas au manifeste.")
    if hashlib.sha256(raw).hexdigest() != manifest["journal_sha256"]:
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
    _check_parent_components(source)
    _check_parent_components(destination)
    if destination.exists() or destination.is_symlink():
        raise AuditArchiveError("Le dossier d'archive existe déjà; aucun écrasement n'est autorisé.")
    try:
        events_before = read_events(source)
        raw = _read_private_file(source, MAX_JOURNAL_BYTES)
    except (AuditError, AuditArchiveError, OSError) as exc:
        raise AuditArchiveError("Le journal source ne peut pas être archivé en toute sécurité.") from exc
    events = _verify_journal_bytes(raw)
    if events != events_before or not events:
        raise AuditArchiveError("Le journal a changé ou est vide pendant la préparation de l'archive.")
    chain = anchor_client.verify_chain()
    if not chain:
        raise AuditArchiveError("Un checkpoint d'ancrage est obligatoire avant archivage.")
    checkpoint = _verified_anchor(anchor_client, chain[-1]["checkpoint_id"], require_head=True)
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
        _check_private_directory(destination)
        _write_new_private_file(destination / JOURNAL_NAME, raw)
        created.append(destination / JOURNAL_NAME)
        _write_new_private_file(destination / MANIFEST_NAME, manifest_bytes)
        created.append(destination / MANIFEST_NAME)
        # Persist both archive entries and the archive directory's own parent entry.
        _fsync_directory(destination)
        _fsync_directory(destination.parent)
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
        try:
            _fsync_directory(destination.parent)
        except AuditArchiveError:
            pass
        raise


def restore_verified_archive(
    archive_directory: str | Path,
    destination_journal: str | Path,
    anchor_client: AnchorClient,
) -> dict[str, Any]:
    """Restaure uniquement vers un chemin absent, après vérification complète."""
    destination = Path(destination_journal)
    _check_parent_components(destination)
    _manifest, raw, events = _load_verified_archive(archive_directory, anchor_client)
    created = False
    try:
        _write_new_private_file(destination, raw)
        created = True
        restored = read_events(destination)
        if restored != events:
            raise AuditArchiveError("Le journal restauré ne correspond pas à l'archive.")
        # read_events also creates the lock file; persist both directory entries.
        _fsync_directory(destination.parent)
    except BaseException:
        if created:
            try:
                destination.unlink()
            except OSError:
                pass
            try:
                _fsync_directory(destination.parent)
            except AuditArchiveError:
                pass
        raise
    return {
        "restored": True,
        "event_count": len(events),
        "last_event_hash": events[-1]["event_hash"],
    }


MAX_RECOVERY_SCAN_ENTRIES = 4096


def _open_inspection_directory(
    path: Path, *, require_private: bool, dir_fd: int | None = None
) -> int:
    """Ouvre un répertoire sans suivre son dernier composant symbolique."""
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory_flag = getattr(os, "O_DIRECTORY", None)
    if nofollow is None or directory_flag is None:
        raise AuditArchiveError(
            "La plateforme ne permet pas une inspection de répertoire sans lien symbolique."
        )
    try:
        descriptor = os.open(path, os.O_RDONLY | directory_flag | nofollow, dir_fd=dir_fd)
    except OSError as exc:
        raise AuditArchiveError("Répertoire absent ou inaccessible pour inspection.") from exc
    info = os.fstat(descriptor)
    if not stat.S_ISDIR(info.st_mode):
        os.close(descriptor)
        raise AuditArchiveError("Le chemin inspecté n'est pas un répertoire réel.")
    if require_private:
        if stat.S_IMODE(info.st_mode) & 0o077:
            os.close(descriptor)
            raise AuditArchiveError("Le répertoire d'archive doit être privé (0700).")
        if not hasattr(os, "geteuid") or info.st_uid != os.geteuid():
            os.close(descriptor)
            raise AuditArchiveError("Le répertoire d'archive doit appartenir au processus courant.")
    return descriptor


def _open_directory_chain(path: Path, *, require_private: bool) -> int:
    """Ouvre chaque composant du chemin relativement au descripteur précédent.

    O_NOFOLLOW est appliqué à chaque composant, pas seulement au dernier :
    un remplacement symbolique d'un ancêtre après son ouverture ne redirige
    donc pas les opérations suivantes vers un autre arbre de répertoires.
    """
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory_flag = getattr(os, "O_DIRECTORY", None)
    if nofollow is None or directory_flag is None:
        raise AuditArchiveError(
            "La plateforme ne permet pas de parcourir les répertoires sans suivre de liens symboliques."
        )
    flags = os.O_RDONLY | directory_flag | nofollow
    start = path.anchor or "."
    try:
        descriptor = os.open(start, flags)
    except OSError as exc:
        raise AuditArchiveError("Impossible d'ouvrir le point de départ du chemin d'inspection.") from exc
    opened = [descriptor]
    try:
        components = path.parts[1:] if path.is_absolute() else path.parts
        for component in components:
            if component in {"", "."}:
                continue
            try:
                child = os.open(component, flags, dir_fd=opened[-1])
            except OSError as exc:
                raise AuditArchiveError(
                    "Un composant du chemin d'inspection est absent, symbolique ou inaccessible."
                ) from exc
            opened.append(child)
            try:
                info = os.fstat(child)
            except OSError as exc:
                raise AuditArchiveError(
                    "Impossible de vérifier un composant du chemin d'inspection."
                ) from exc
            if not stat.S_ISDIR(info.st_mode):
                raise AuditArchiveError("Chaque composant du chemin d'inspection doit être un répertoire.")
        info = os.fstat(opened[-1])
        if require_private:
            if stat.S_IMODE(info.st_mode) & 0o077:
                raise AuditArchiveError("Le répertoire doit être privé (0700).")
            if not hasattr(os, "geteuid") or info.st_uid != os.geteuid():
                raise AuditArchiveError("Le répertoire doit appartenir au processus courant.")
        result = opened[-1]
        for previous in opened[:-1]:
            try:
                os.close(previous)
            except OSError:
                pass
        return result
    except BaseException:
        for descriptor in reversed(opened):
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise


def _inspection_entry(directory_fd: int, name: str, maximum: int) -> dict[str, Any]:
    """Retourne uniquement des métadonnées obtenues sans suivre le lien éventuel."""
    try:
        info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except OSError:
        return {"name": name, "kind": "unavailable", "safe_to_inspect": False}
    if stat.S_ISLNK(info.st_mode):
        kind = "symlink"
    elif stat.S_ISREG(info.st_mode):
        kind = "regular"
    elif stat.S_ISDIR(info.st_mode):
        kind = "directory"
    else:
        kind = "other"
    owner_matches = hasattr(os, "geteuid") and info.st_uid == os.geteuid()
    private = not bool(stat.S_IMODE(info.st_mode) & 0o077)
    size_ok = kind == "regular" and info.st_size <= maximum
    return {
        "name": name,
        "kind": kind,
        "size_bytes": info.st_size if kind == "regular" else None,
        "mode": format(stat.S_IMODE(info.st_mode), "04o"),
        "owner_matches": bool(owner_matches),
        "private": private,
        "within_size_limit": size_ok,
        "safe_to_inspect": bool(kind == "regular" and owner_matches and private and size_ok),
    }


def _temporary_name(name: str, target_name: str) -> bool:
    prefix = f".{target_name}."
    return name.startswith(prefix) and name.endswith(".tmp") and len(name) > len(prefix) + 4


def inspect_archive_recovery(path: str | Path, *, kind: str) -> dict[str, Any]:
    """Inventorie en lecture seule une archive ou les temporaires d'une restauration.

    Aucun contenu n'est chargé, renommé, promu ou supprimé. Les temporaires ne
    disposent pas seuls d'une preuve de contenu suffisante pour être restaurés.
    """
    target = Path(path)
    if not target.name or target.name in {".", ".."}:
        raise AuditArchiveError("Le chemin d'inspection doit désigner un nom explicite.")
    if kind not in {"archive-directory", "restore-target"}:
        raise AuditArchiveError("Type d'inspection inconnu.")
    # Walk every parent component through pinned directory descriptors.
    # A path-based lstat followed by a single open would leave an ancestor
    # replacement window even if the final component used O_NOFOLLOW.
    parent_fd = _open_directory_chain(target.parent, require_private=False)
    try:
        try:
            target_info = os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
            target_exists = True
        except FileNotFoundError:
            target_info = None
            target_exists = False
        except OSError as exc:
            raise AuditArchiveError("Impossible d'inspecter le chemin cible.") from exc

        if kind == "restore-target":
            candidates: list[dict[str, Any]] = []
            truncated = False
            with os.scandir(parent_fd) as iterator:
                scanned = 0
                for entry in iterator:
                    scanned += 1
                    if scanned > MAX_RECOVERY_SCAN_ENTRIES:
                        truncated = True
                        break
                    if _temporary_name(entry.name, target.name):
                        candidates.append(_inspection_entry(parent_fd, entry.name, MAX_JOURNAL_BYTES))
            if target_exists:
                target_kind = (
                    "symlink" if stat.S_ISLNK(target_info.st_mode)
                    else "regular" if stat.S_ISREG(target_info.st_mode)
                    else "directory" if stat.S_ISDIR(target_info.st_mode)
                    else "other"
                )
                status = "target_exists_no_recovery"
            elif truncated:
                target_kind = "absent"
                status = "scan_limit_exceeded"
            elif candidates:
                target_kind = "absent"
                status = "temporary_candidates_review_required"
            else:
                target_kind = "absent"
                status = "no_temporary_candidates"
            return {
                "kind": kind,
                "target_name": target.name,
                "target_state": target_kind,
                "status": status,
                "temporary_candidates": candidates,
                "scan_truncated": truncated,
                "automatic_recovery": False,
                "recommended_action": (
                    "Ne jamais promouvoir ni supprimer automatiquement un temporaire : "
                    "son contenu n'est pas lié à un manifeste et à un checkpoint vérifiés. "
                    "Préserver les éléments et, si l'archive source est intacte, restaurer "
                    "vers un nouveau chemin avec restore_verified_archive."
                ),
            }

        if not target_exists:
            return {
                "kind": kind,
                "target_name": target.name,
                "status": "archive_directory_missing",
                "entries": [],
                "temporary_candidates": [],
                "automatic_recovery": False,
                "recommended_action": (
                    "Aucun temporaire d'archive n'est attendu dans un dossier absent. "
                    "Ne pas reconstruire à partir de fragments non vérifiés."
                ),
            }
        if not stat.S_ISDIR(target_info.st_mode) or stat.S_ISLNK(target_info.st_mode):
            return {
                "kind": kind,
                "target_name": target.name,
                "status": "unsafe_archive_path",
                "entries": [],
                "temporary_candidates": [],
                "automatic_recovery": False,
                "recommended_action": "Ne pas suivre ni modifier ce chemin ; inspection humaine requise.",
            }

        try:
            archive_fd = _open_inspection_directory(
                Path(target.name), require_private=True, dir_fd=parent_fd
            )
        except AuditArchiveError:
            return {
                "kind": kind,
                "target_name": target.name,
                "status": "unsafe_archive_directory",
                "entries": [],
                "temporary_candidates": [],
                "automatic_recovery": False,
                "recommended_action": "Ne pas modifier ce dossier ; vérifier manuellement propriétaire et permissions.",
            }
        try:
            names: list[str] = []
            truncated = False
            with os.scandir(archive_fd) as iterator:
                for entry in iterator:
                    if len(names) >= MAX_RECOVERY_SCAN_ENTRIES:
                        truncated = True
                        break
                    names.append(entry.name)
            names.sort()
            entries = [
                _inspection_entry(
                    archive_fd, name,
                    MAX_MANIFEST_BYTES
                    if name == MANIFEST_NAME or _temporary_name(name, MANIFEST_NAME)
                    else MAX_JOURNAL_BYTES,
                )
                for name in names
            ]
            temporary_candidates = [
                item for item in entries
                if _temporary_name(item["name"], MANIFEST_NAME)
                or _temporary_name(item["name"], JOURNAL_NAME)
            ]
            unexpected_entries = [
                item for item in entries
                if item["name"] not in {MANIFEST_NAME, JOURNAL_NAME}
                and item not in temporary_candidates
            ]
            by_name = {item["name"]: item for item in entries}
            expected_safe = all(
                name in by_name and by_name[name]["safe_to_inspect"]
                for name in (MANIFEST_NAME, JOURNAL_NAME)
            )
            exact_structure = (
                not truncated
                and set(names) == {MANIFEST_NAME, JOURNAL_NAME}
                and expected_safe
            )
            return {
                "kind": kind,
                "target_name": target.name,
                "status": "structurally_complete_unverified" if exact_structure else (
                    "scan_limit_exceeded" if truncated else "incomplete"
                ),
                "entries": entries,
                "temporary_candidates": temporary_candidates,
                "unexpected_entries": unexpected_entries,
                "scan_truncated": truncated,
                "cryptographic_verification_performed": False,
                "automatic_recovery": False,
                "recommended_action": (
                    "La structure semble complète, mais ce rapport ne vérifie ni le SHA-256 "
                    "du manifeste, ni le JSONL, ni le checkpoint. Appeler verify_archive avec "
                    "un AnchorClient autorisé avant toute confiance."
                    if exact_structure else
                    "Préserver tous les fichiers. Ne pas promouvoir, renommer ou supprimer "
                    "les temporaires. Si le journal source est encore disponible et vérifié, "
                    "recréer une archive vers un nouveau répertoire absent."
                ),
            }
        finally:
            os.close(archive_fd)
    finally:
        os.close(parent_fd)
