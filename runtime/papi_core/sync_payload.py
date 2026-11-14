"""Paquets de contenu mémoire/chat liés aux références d'un bundle signé."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path
from typing import Any

from .chat import AGENTS_FILE, validate_message, ChatError
from .memory import _validate_event, MemoryError
from .registry import load_agents, RegistryError
from .sync_bundle import SyncBundleError, validate_sync_bundle

FORMAT_VERSION = 1
MAX_PAYLOAD_BYTES = 2 * 1024 * 1024
_NAME = re.compile(r"^[a-f0-9]{64}\.papidata$")
_EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_PHONE = re.compile(r"(?<!\w)(?:\+?221[ .-]?)?(?:7[0678])[ .-]?\d{3}[ .-]?\d{2}[ .-]?\d{2}(?!\w)")
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")


class SyncPayloadError(ValueError):
    """Contenu sync non conforme, sensible ou non lié au bundle signé."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as exc:
        raise SyncPayloadError("Contenu non sérialisable de manière canonique.") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _privacy_check(record: dict[str, Any]) -> None:
    raw = _canonical(record).decode("utf-8")
    if _EMAIL.search(raw) or _PHONE.search(raw) or _CARD.search(raw):
        raise SyncPayloadError("Donnée personnelle ou financière potentielle détectée; export refusé.")


def _record_identity(kind: str, record: dict[str, Any], agents_path: Path) -> tuple[str, str]:
    if kind == "memory":
        try:
            _validate_event(record, 1)
        except (MemoryError, TypeError, KeyError, AttributeError) as exc:
            raise SyncPayloadError("Événement mémoire invalide.") from exc
        if record.get("event_type") != "remember":
            raise SyncPayloadError("Seuls les événements remember peuvent être exportés.")
        try:
            known_agents = load_agents(Path(agents_path))
        except RegistryError as exc:
            raise SyncPayloadError("Registre d’agents indisponible; export mémoire refusé.") from exc
        if record.get("actor") not in known_agents:
            raise SyncPayloadError("Auteur mémoire absent du registre d’agents.")
        if record.get("scope") != "shared" or record.get("sensitivity") != "normal":
            raise SyncPayloadError("Seules les mémoires partagées et de sensibilité normale sont exportables.")
        if record.get("category") == "decision":
            raise SyncPayloadError("Les décisions officielles ne sont pas exportables par ce mécanisme.")
        return record["event_id"], record["memory_id"]
    if kind == "message":
        try:
            validate_message(record, agents_path)
        except (ChatError, TypeError, KeyError, AttributeError) as exc:
            raise SyncPayloadError("Message PAPI CHAT invalide.") from exc
        return record["message_id"], record["message_id"]
    raise SyncPayloadError("Type de contenu non pris en charge.")


def build_sync_payload(*, bundle: dict[str, Any], records: list[dict[str, Any]],
                       agents_path: Path = AGENTS_FILE) -> dict[str, Any]:
    """Construit une charge utile dont chaque contenu correspond au digest approuvé."""
    try:
        validate_sync_bundle(bundle)
    except (SyncBundleError, TypeError, KeyError, AttributeError) as exc:
        raise SyncPayloadError("Bundle de référence invalide.") from exc
    if not isinstance(records, list) or len(records) != len(bundle["events"]):
        raise SyncPayloadError("Le contenu doit couvrir exactement les références du bundle.")
    by_id: dict[str, dict[str, Any]] = {}
    for item in records:
        if not isinstance(item, dict) or set(item) != {"kind", "record"}:
            raise SyncPayloadError("Entrée de contenu mal formée.")
        kind, record = item["kind"], item["record"]
        if not isinstance(record, dict):
            raise SyncPayloadError("Chaque contenu doit être un objet JSON.")
        event_id, record_id = _record_identity(kind, record, Path(agents_path))
        if event_id in by_id:
            raise SyncPayloadError("Identifiant de contenu dupliqué.")
        _privacy_check(record)
        by_id[event_id] = {"kind": kind, "record_id": record_id,
                           "event_id": event_id, "content_digest": _digest(record),
                           "record": record}
    normalized = []
    for reference in bundle["events"]:
        item = by_id.get(reference["event_id"])
        if (item is None or item["kind"] != reference["kind"]
                or item["record_id"] != reference["record_id"]
                or item["content_digest"] != reference["content_digest"]):
            raise SyncPayloadError("Contenu absent ou différent de l'empreinte approuvée.")
        normalized.append(item)
    body = {"format_version": FORMAT_VERSION, "bundle_digest": bundle["bundle_digest"],
            "records": normalized}
    payload = {**body, "payload_digest": _digest(body)}
    if len(_canonical(payload)) > MAX_PAYLOAD_BYTES:
        raise SyncPayloadError("Charge utile supérieure à 2 Mio.")
    return payload


def validate_sync_payload(payload: object, *, bundle: dict[str, Any],
                          agents_path: Path = AGENTS_FILE) -> bool:
    if not isinstance(payload, dict) or set(payload) != {
        "format_version", "bundle_digest", "records", "payload_digest"
    } or isinstance(payload.get("format_version"), bool) or payload.get("format_version") != FORMAT_VERSION:
        raise SyncPayloadError("Enveloppe de charge utile invalide.")
    body = {key: payload[key] for key in ("format_version", "bundle_digest", "records")}
    if not isinstance(payload["payload_digest"], str) or _digest(body) != payload["payload_digest"]:
        raise SyncPayloadError("Empreinte de charge utile invalide.")
    expected = build_sync_payload(
        bundle=bundle,
        records=[{"kind": item.get("kind"), "record": item.get("record")}
                 for item in payload["records"] if isinstance(item, dict)],
        agents_path=agents_path,
    )
    if _canonical(expected) != _canonical(payload):
        raise SyncPayloadError("Charge utile non conforme au bundle ou non canonique.")
    return True


def write_sync_payload(*, bundle: dict[str, Any], records: list[dict[str, Any]],
                       spool_dir: Path, agents_path: Path = AGENTS_FILE) -> dict[str, Any]:
    payload = build_sync_payload(bundle=bundle, records=records, agents_path=agents_path)
    raw = _canonical(payload)
    directory = Path(spool_dir)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if directory.is_symlink() or not directory.is_dir():
        raise SyncPayloadError("Le répertoire de charge utile doit être un dossier local réel.")
    os.chmod(directory, 0o700)
    destination = directory / (payload["payload_digest"] + ".papidata")
    fd, temporary = tempfile.mkstemp(prefix=".papi-data-", suffix=".tmp", dir=directory)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination, follow_symlinks=False)
        except FileExistsError as exc:
            raise SyncPayloadError("Cette charge utile existe déjà; aucun écrasement effectué.") from exc
        dirfd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return {"status": "staged", "path": str(destination),
            "payload_digest": payload["payload_digest"], "size_bytes": len(raw),
            "signature_verified": False, "import_performed": False,
            "execution_enabled": False}


def read_sync_payload(path: Path, *, bundle: dict[str, Any],
                      agents_path: Path = AGENTS_FILE) -> dict[str, Any]:
    path = Path(path)
    if not _NAME.fullmatch(path.name):
        raise SyncPayloadError("Nom de charge utile non conforme.")
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size <= 0 or info.st_size > MAX_PAYLOAD_BYTES:
                raise SyncPayloadError("Fichier absent, non régulier, vide ou trop volumineux.")
            chunks, remaining = [], MAX_PAYLOAD_BYTES + 1
            while remaining:
                chunk = os.read(fd, min(65536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            if len(raw) > MAX_PAYLOAD_BYTES:
                raise SyncPayloadError("Charge utile supérieure à 2 Mio.")
        finally:
            os.close(fd)
    except OSError as exc:
        raise SyncPayloadError("Fichier inaccessible ou lien symbolique refusé.") from exc
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SyncPayloadError("JSON de charge utile invalide.") from exc
    validate_sync_payload(payload, bundle=bundle, agents_path=agents_path)
    if raw != _canonical(payload) or path.name != payload["payload_digest"] + ".papidata":
        raise SyncPayloadError("Encodage canonique ou nom de fichier incohérent.")
    return payload


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise SyncPayloadError("Clé JSON dupliquée.")
        result[key] = value
    return result
