"""Manifeste de transfert hors ligne liant paquet approuvé et charge utile.

Ce module prépare un transfert vérifiable sans ouvrir de connexion réseau,
sans consommer de nonce et sans importer de contenu.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

from .sync_spool import MAX_PACKAGE_BYTES

MAX_TRANSFER_BYTES = 4 * 1024 * 1024
_DIGEST = re.compile(r"^[a-f0-9]{64}$")
_PACKAGE_NAME = re.compile(r"^[a-f0-9]{64}\.papisync$")
_PAYLOAD_NAME = re.compile(r"^[a-f0-9]{64}\.papidata$")


class SyncTransferManifestError(ValueError):
    """Manifeste de transfert invalide ou fichier source non sûr."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as exc:
        raise SyncTransferManifestError("Données non sérialisables de manière canonique.") from exc


def _read_regular(path: Path, *, maximum: int) -> bytes:
    path = Path(path)
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size <= 0 or info.st_size > maximum:
                raise SyncTransferManifestError("Fichier absent, non régulier, vide ou trop volumineux.")
            chunks: list[bytes] = []
            remaining = maximum + 1
            while remaining:
                chunk = os.read(fd, min(65536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            if len(raw) > maximum:
                raise SyncTransferManifestError("Fichier supérieur à la limite autorisée.")
            return raw
        finally:
            os.close(fd)
    except OSError as exc:
        raise SyncTransferManifestError("Fichier inaccessible ou lien symbolique refusé.") from exc


def _decode_canonical(raw: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(
                               SyncTransferManifestError("Constante JSON interdite.")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SyncTransferManifestError(f"{label} JSON invalide.") from exc
    if not isinstance(value, dict) or raw != _canonical(value):
        raise SyncTransferManifestError(f"{label} non canonique ou enveloppe invalide.")
    return value


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SyncTransferManifestError("Clé JSON dupliquée.")
        result[key] = value
    return result


def build_sync_transfer_manifest(*, package_path: Path, payload_path: Path) -> dict[str, Any]:
    """Construit un manifeste déterministe liant les deux fichiers d'un transfert."""
    package_path, payload_path = Path(package_path), Path(payload_path)
    if not _PACKAGE_NAME.fullmatch(package_path.name):
        raise SyncTransferManifestError("Nom de paquet .papisync non conforme.")
    if not _PAYLOAD_NAME.fullmatch(payload_path.name):
        raise SyncTransferManifestError("Nom de charge utile .papidata non conforme.")
    package_raw = _read_regular(package_path, maximum=MAX_PACKAGE_BYTES)
    payload_raw = _read_regular(payload_path, maximum=MAX_TRANSFER_BYTES - MAX_PACKAGE_BYTES)
    package = _decode_canonical(package_raw, label="Paquet")
    payload = _decode_canonical(payload_raw, label="Charge utile")

    if set(package) != {"format_version", "bundle", "approval", "package_digest"}:
        raise SyncTransferManifestError("Enveloppe du paquet inattendue.")
    package_body = {key: package[key] for key in ("format_version", "bundle", "approval")}
    package_digest = hashlib.sha256(_canonical(package_body)).hexdigest()
    if package.get("package_digest") != package_digest or package_path.name != package_digest + ".papisync":
        raise SyncTransferManifestError("Digest ou nom du paquet incohérent.")

    if set(payload) != {"format_version", "bundle_digest", "records", "payload_digest"}:
        raise SyncTransferManifestError("Enveloppe de charge utile inattendue.")
    payload_body = {key: payload[key] for key in ("format_version", "bundle_digest", "records")}
    payload_digest = hashlib.sha256(_canonical(payload_body)).hexdigest()
    if payload.get("payload_digest") != payload_digest or payload_path.name != payload_digest + ".papidata":
        raise SyncTransferManifestError("Digest ou nom de la charge utile incohérent.")

    bundle = package.get("bundle")
    if not isinstance(bundle, dict) or not _DIGEST.fullmatch(str(bundle.get("bundle_digest", ""))):
        raise SyncTransferManifestError("Bundle de référence invalide.")
    if payload.get("bundle_digest") != bundle["bundle_digest"]:
        raise SyncTransferManifestError("La charge utile ne correspond pas au bundle du paquet.")
    source = bundle.get("source_instance_id")
    destination = bundle.get("destination_instance_id")
    export_id = bundle.get("export_id")
    if not all(isinstance(item, str) and item for item in (source, destination, export_id)):
        raise SyncTransferManifestError("Métadonnées de routage du bundle absentes.")
    if package.get("approval", {}).get("payload", {}).get("destination_instance_id") != destination:
        raise SyncTransferManifestError("Destination du paquet et approbation différentes.")

    core = {
        "format_version": 1,
        "protocol": "papi.sync.transfer-manifest",
        "package": {"filename": package_path.name, "sha256": hashlib.sha256(package_raw).hexdigest(),
                    "size_bytes": len(package_raw), "package_digest": package_digest},
        "payload": {"filename": payload_path.name, "sha256": hashlib.sha256(payload_raw).hexdigest(),
                    "size_bytes": len(payload_raw), "payload_digest": payload_digest},
        "bundle_digest": bundle["bundle_digest"],
        "source_instance_id": source,
        "destination_instance_id": destination,
        "export_id": export_id,
        "requires_destination_authentication": True,
        "requires_owner_approval": True,
        "nonce_consumption": "receiver_only",
        "import_performed": False,
        "network_transfer_performed": False,
        "execution_enabled": False,
    }
    if len(package_raw) + len(payload_raw) > MAX_TRANSFER_BYTES:
        raise SyncTransferManifestError("Transfert supérieur à la taille maximale autorisée.")
    delivery_id = hashlib.sha256(_canonical(core)).hexdigest()
    return {**core, "delivery_id": delivery_id}


def validate_sync_transfer_manifest(manifest: object) -> bool:
    """Valide la cohérence interne du manifeste; ne donne aucune autorisation."""
    if not isinstance(manifest, dict):
        raise SyncTransferManifestError("Manifeste absent ou invalide.")
    required = {
        "format_version", "protocol", "package", "payload", "bundle_digest",
        "source_instance_id", "destination_instance_id", "export_id",
        "requires_destination_authentication", "requires_owner_approval",
        "nonce_consumption", "import_performed", "network_transfer_performed",
        "execution_enabled", "delivery_id",
    }
    if set(manifest) != required:
        raise SyncTransferManifestError("Champs du manifeste inattendus.")
    if (manifest["format_version"] != 1 or isinstance(manifest["format_version"], bool)
            or manifest["protocol"] != "papi.sync.transfer-manifest"
            or manifest["requires_destination_authentication"] is not True
            or manifest["requires_owner_approval"] is not True
            or manifest["nonce_consumption"] != "receiver_only"
            or manifest["import_performed"] is not False
            or manifest["network_transfer_performed"] is not False
            or manifest["execution_enabled"] is not False):
        raise SyncTransferManifestError("Contrat de sécurité du manifeste invalide.")
    for label, suffix, digest_key in (("package", ".papisync", "package_digest"),
                                      ("payload", ".papidata", "payload_digest")):
        item = manifest[label]
        if not isinstance(item, dict) or set(item) != {"filename", "sha256", "size_bytes", digest_key}:
            raise SyncTransferManifestError(f"Métadonnées {label} invalides.")
        if (not isinstance(item["filename"], str) or not _DIGEST.fullmatch(str(item["sha256"]))
                or item["filename"] != item[digest_key] + suffix
                or not _DIGEST.fullmatch(str(item[digest_key]))
                or isinstance(item["size_bytes"], bool) or not isinstance(item["size_bytes"], int)
                or item["size_bytes"] <= 0):
            raise SyncTransferManifestError(f"Champs {label} invalides.")
    for key in ("bundle_digest",):
        if not isinstance(manifest[key], str) or not _DIGEST.fullmatch(manifest[key]):
            raise SyncTransferManifestError("Digest de bundle invalide.")
    for key in ("source_instance_id", "destination_instance_id", "export_id"):
        if not isinstance(manifest[key], str) or not manifest[key].strip():
            raise SyncTransferManifestError("Identifiant de routage invalide.")
    core = {key: value for key, value in manifest.items() if key != "delivery_id"}
    if not isinstance(manifest["delivery_id"], str) or hashlib.sha256(_canonical(core)).hexdigest() != manifest["delivery_id"]:
        raise SyncTransferManifestError("Digest du manifeste de transfert invalide.")
    if manifest["package"]["size_bytes"] + manifest["payload"]["size_bytes"] > MAX_TRANSFER_BYTES:
        raise SyncTransferManifestError("Transfert supérieur à la taille maximale autorisée.")
    return True
