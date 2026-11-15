"""Verify detached Ed25519 signatures over immutable artifact bytes.

This module is verification-only: it never loads, creates, or modifies private keys.
"""
from __future__ import annotations

import hashlib
import hmac
import re
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .identity_ed25519 import (
    Ed25519IdentityError,
    _read_registry,
    _validate_agent,
    _validated_registry_key_record,
)
from .identity_reconciliation_artifact import MAX_RECONCILIATION_REPORT_BYTES


class ArtifactSignatureError(ValueError):
    """A detached artifact signature or its trusted identity is invalid."""


_REQUIRED_PROOF_FIELDS = {
    "schema_version", "algorithm", "agent_id", "key_version",
    "artifact_sha256", "signature",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def verify_reconciliation_artifact_signature(
    raw_artifact: bytes,
    proof: dict[str, Any],
    registry_path: Path,
) -> dict[str, Any]:
    """Verify exact artifact bytes against a versioned trusted public key.

    Historical keys and revoked identities remain verifiable for provenance
    audits only. A successful result never grants authorization or consumes
    an anti-replay nonce.
    """
    if not isinstance(raw_artifact, bytes):
        raise ArtifactSignatureError("L'artefact doit être fourni en octets.")
    if len(raw_artifact) > MAX_RECONCILIATION_REPORT_BYTES:
        raise ArtifactSignatureError("Artefact trop volumineux.")
    if not isinstance(proof, dict) or set(proof) != _REQUIRED_PROOF_FIELDS:
        raise ArtifactSignatureError("Preuve de signature invalide.")
    if type(proof["schema_version"]) is not int or proof["schema_version"] != 1:
        raise ArtifactSignatureError("Version de preuve invalide.")
    if proof["algorithm"] != "Ed25519":
        raise ArtifactSignatureError("Algorithme de signature interdit.")
    agent_id = proof["agent_id"]
    version = proof["key_version"]
    if type(version) is not int or version < 1:
        raise ArtifactSignatureError("Version de clé invalide.")
    digest = proof["artifact_sha256"]
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        raise ArtifactSignatureError("Digest d'artefact invalide.")
    actual_digest = hashlib.sha256(raw_artifact).hexdigest()
    if not hmac.compare_digest(digest, actual_digest):
        raise ArtifactSignatureError("Le digest de l'artefact ne correspond pas.")
    signature_hex = proof["signature"]
    if not isinstance(signature_hex, str):
        raise ArtifactSignatureError("Signature invalide.")
    try:
        signature = bytes.fromhex(signature_hex)
    except ValueError as exc:
        raise ArtifactSignatureError("Signature invalide.") from exc
    if len(signature) != 64:
        raise ArtifactSignatureError("Longueur de signature invalide.")

    try:
        _validate_agent(agent_id)
        registry = _read_registry(Path(registry_path))
        record = registry["agents"].get(agent_id)
        if not isinstance(record, dict) or record.get("status") not in {"active", "revoked"}:
            raise ArtifactSignatureError("Identité inconnue ou statut invalide.")
        current_version, current_public, history = _validated_registry_key_record(record)
        if current_version == version:
            public_bytes = current_public
        else:
            matches = [
                bytes.fromhex(item["public_key"])
                for item in history if item["key_version"] == version
            ]
            if len(matches) != 1:
                raise ArtifactSignatureError("Version de clé absente ou ambiguë.")
            public_bytes = matches[0]
        Ed25519PublicKey.from_public_bytes(public_bytes).verify(signature, raw_artifact)
    except ArtifactSignatureError:
        raise
    except (Ed25519IdentityError, OSError, ValueError, TypeError, InvalidSignature) as exc:
        raise ArtifactSignatureError("Vérification de provenance Ed25519 refusée.") from exc

    return {
        "signature_verified": True,
        "agent_id": agent_id,
        "key_version": version,
        "algorithm": "Ed25519",
        "historical_key": current_version != version,
        "identity_status": record["status"],
        "authorization_granted": False,
        "nonce_consumed": False,
    }
