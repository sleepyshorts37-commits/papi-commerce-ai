"""Construction locale d'une requête de transport HTTPS, sans émission réseau."""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .sync_transfer_manifest import (
    MAX_TRANSFER_BYTES,
    SyncTransferManifestError,
    _read_regular,
    verify_sync_transfer_manifest_files,
)

class SyncTransportPlanError(ValueError):
    """Destination ou contenu de transport refusé."""

def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as exc:
        raise SyncTransportPlanError("Requête non canonique.") from exc

def _validate_endpoint(endpoint: object, allowed_hosts: object) -> str:
    if not isinstance(endpoint, str) or not isinstance(allowed_hosts, (set, frozenset, list, tuple)):
        raise SyncTransportPlanError("Endpoint HTTPS et liste d'hôtes autorisés requis.")
    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError as exc:
        raise SyncTransportPlanError("Endpoint invalide.") from exc
    host = parsed.hostname
    if (parsed.scheme != "https" or not host or parsed.username is not None
        or parsed.password is not None or parsed.query or parsed.fragment
        or port not in (None, 443) or not host.isascii()
        or host.endswith(".") or not re.fullmatch(r"[a-zA-Z0-9.-]+", host)):
        raise SyncTransportPlanError("Seuls les endpoints HTTPS publics sans identifiants sont acceptés.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise SyncTransportPlanError("Adresse IP non publique interdite.")
    normalized = host.lower()
    if normalized == "localhost" or normalized.endswith((".localhost", ".local", ".internal", ".test")):
        raise SyncTransportPlanError("Nom d’hôte local ou réservé interdit.")
    permitted = {item.lower() for item in allowed_hosts
                 if isinstance(item, str) and item.isascii()}
    if normalized not in permitted:
        raise SyncTransportPlanError("Hôte absent de la liste d'autorisation.")
    path = parsed.path or "/"
    if not path.startswith("/") or "\\" in path or any(part in (".", "..") for part in path.split("/")):
        raise SyncTransportPlanError("Chemin endpoint non conforme.")
    return endpoint

def build_sync_transport_request(
    *, manifest: object, directory: Path, endpoint: str,
    allowed_hosts: set[str] | frozenset[str] | tuple[str, ...] | list[str],
) -> dict[str, Any]:
    """Construit une requête HTTPS déterministe prête à transmettre, mais ne l'envoie jamais."""
    try:
        verify_sync_transfer_manifest_files(manifest, directory=Path(directory))
    except SyncTransferManifestError as exc:
        raise SyncTransportPlanError(str(exc)) from exc
    destination = _validate_endpoint(endpoint, allowed_hosts)
    if manifest["network_transfer_performed"] is not False:
        raise SyncTransportPlanError("Manifeste déjà marqué comme transféré.")
    root = Path(directory)
    package = _read_regular(root / manifest["package"]["filename"], maximum=2 * 1024 * 1024)
    payload = _read_regular(root / manifest["payload"]["filename"],
                            maximum=MAX_TRANSFER_BYTES - 2 * 1024 * 1024)
    body = {
        "protocol": "papi.sync.transport-request",
        "protocol_version": 1,
        "delivery_id": manifest["delivery_id"],
        "source_instance_id": manifest["source_instance_id"],
        "destination_instance_id": manifest["destination_instance_id"],
        "manifest": manifest,
        "package_base64": base64.b64encode(package).decode("ascii"),
        "payload_base64": base64.b64encode(payload).decode("ascii"),
    }
    raw = _canonical(body)
    if len(raw) > 2 * MAX_TRANSFER_BYTES:
        raise SyncTransportPlanError("Requête encodée supérieure à la limite autorisée.")
    return {
        "method": "POST",
        "url": destination,
        "headers": {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Idempotency-Key": manifest["delivery_id"],
        },
        "body": body,
        "body_sha256": hashlib.sha256(raw).hexdigest(),
        "body_size_bytes": len(raw),
        "network_transfer_performed": False,
        "nonce_consumed": False,
        "receipt_committed": False,
        "import_performed": False,
        "execution_enabled": False,
        "receiver_authentication_required": True,
        "receiver_reverification_required": True,
        "tls_verification_required": True,
        "redirects_allowed": False,
    }
