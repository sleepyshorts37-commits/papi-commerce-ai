"""Vérification locale d'un reçu de transport signé par l'instance cible."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .identity_ed25519 import Ed25519IdentityError, verify_ed25519_request, verify_ed25519_request_transactional


class SyncTransportReceiptError(ValueError):
    """Reçu absent, non authentique ou lié à une autre livraison."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as exc:
        raise SyncTransportReceiptError("Reçu non canonique.") from exc


def verify_sync_transport_receipt(
    *, request: object, receipt: object, registry_path: Path,
    replay_db: Path, now: int | None = None,
    replay_connection: Any | None = None,
) -> dict[str, Any]:
    """Authentifie le destinataire et lie son reçu à la requête exacte.

    Le nonce du reçu n'est consommé qu'après validation cryptographique et
    correspondance complète des identifiants et digests. Aucun réseau, import
    ou changement d'état de transfert n'est effectué.
    """
    if not isinstance(request, dict) or set(request) != {
        "method", "url", "headers", "body", "body_sha256", "body_size_bytes",
        "network_transfer_performed", "nonce_consumed", "receipt_committed",
        "import_performed", "execution_enabled", "receiver_authentication_required",
        "receiver_reverification_required", "tls_verification_required", "redirects_allowed",
    }:
        raise SyncTransportReceiptError("Requête de transport invalide.")
    if (request["method"] != "POST" or request["network_transfer_performed"] is not False
        or request["nonce_consumed"] is not False or request["receipt_committed"] is not False
        or request["import_performed"] is not False or request["execution_enabled"] is not False
        or request["receiver_authentication_required"] is not True
        or request["receiver_reverification_required"] is not True
        or request["tls_verification_required"] is not True or request["redirects_allowed"] is not False):
        raise SyncTransportReceiptError("État ou politique de requête non conforme.")
    body = request["body"]
    if not isinstance(body, dict) or body.get("protocol") != "papi.sync.transport-request" or body.get("protocol_version") != 1:
        raise SyncTransportReceiptError("Corps de requête invalide.")
    raw = _canonical(body)
    digest = hashlib.sha256(raw).hexdigest()
    if request["body_sha256"] != digest or request["body_size_bytes"] != len(raw):
        raise SyncTransportReceiptError("Digest ou taille de requête incohérent.")
    manifest = body.get("manifest")
    if not isinstance(manifest, dict):
        raise SyncTransportReceiptError("Manifeste de livraison absent.")
    delivery_id = manifest.get("delivery_id")
    source_id = manifest.get("source_instance_id")
    destination_id = manifest.get("destination_instance_id")
    if (body.get("delivery_id") != delivery_id or body.get("source_instance_id") != source_id
        or body.get("destination_instance_id") != destination_id
        or not isinstance(delivery_id, str) or not isinstance(source_id, str)
        or not isinstance(destination_id, str)):
        raise SyncTransportReceiptError("Routage de requête incohérent.")
    if not isinstance(receipt, dict):
        raise SyncTransportReceiptError("Enveloppe de reçu absente.")
    payload = receipt.get("payload")
    expected = {
        "scope": "papi.sync.transport-receipt",
        "decision": "accepted",
        "receipt_id": None,
        "delivery_id": delivery_id,
        "request_body_sha256": digest,
        "source_instance_id": source_id,
        "destination_instance_id": destination_id,
        "package_digest": manifest.get("package", {}).get("package_digest"),
        "payload_digest": manifest.get("payload", {}).get("payload_digest"),
    }
    if not isinstance(payload, dict) or set(payload) != set(expected):
        raise SyncTransportReceiptError("Contenu du reçu inattendu.")
    for key, value in expected.items():
        if key == "receipt_id":
            if not isinstance(payload[key], str) or not payload[key].strip():
                raise SyncTransportReceiptError("Identifiant de reçu invalide.")
        elif payload[key] != value:
            raise SyncTransportReceiptError("Le reçu ne correspond pas à cette livraison.")
    if receipt.get("agent_id") != destination_id:
        raise SyncTransportReceiptError("Le reçu doit être signé par l'instance destinataire.")
    try:
        if replay_connection is not None:
            # Nonce reservation participates in the caller's SQLite transaction.
            verified = verify_ed25519_request_transactional(
                receipt, connection=replay_connection,
                registry_path=Path(registry_path), now=now,
            )
        else:
            verified = verify_ed25519_request(
                receipt, registry_path=Path(registry_path), replay_db=Path(replay_db),
                now=now, consume_nonce=False,
            )
            # Legacy standalone mode; caller cannot atomically couple a separate ledger.
            verified = verify_ed25519_request(
                receipt, registry_path=Path(registry_path), replay_db=Path(replay_db),
                now=now, consume_nonce=True,
            )
    except Ed25519IdentityError as exc:
        raise SyncTransportReceiptError(str(exc)) from exc
    return {
        "status": "transport_receipt_verified",
        "receipt_id": payload["receipt_id"],
        "delivery_id": delivery_id,
        "request_body_sha256": digest,
        "source_instance_id": source_id,
        "destination_instance_id": destination_id,
        "destination_signature_verified": True,
        "destination_nonce_consumed": verified["nonce_consumed"],
        "network_transfer_performed": False,
        "receipt_committed": False,
        "import_performed": False,
        "execution_enabled": False,
        "manual_reconciliation_required": True,
    }
