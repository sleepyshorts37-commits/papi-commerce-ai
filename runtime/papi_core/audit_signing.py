"""Backend-only signing-provider boundary for audit checkpoints.

Production integrations may implement this protocol with a KMS/HSM or isolated
signing service. This module deliberately contains no cloud SDK, credentials,
network calls, or automatic fallback to local keys.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .audit_anchor_keys import LocalAuditKeyring


class SigningProviderError(RuntimeError):
    """Signing provider is unavailable or rejected an operation."""


@runtime_checkable
class AuditSigningProvider(Protocol):
    """Minimal interface required by checkpoint publication and verification.

    Implementations must keep private key material inside their trust boundary.
    The public key identifier is opaque and stable for historical verification.
    """

    def sign(self, key_id: str, message: bytes) -> str:
        """Return a hexadecimal Ed25519 signature for the exact message."""

    def verify(self, key_id: str, message: bytes, signature_hex: str) -> bool:
        """Verify using retained public material; fail closed on unknown/revoked keys."""


class LocalKeyringSigningProvider:
    """Explicit development/reference adapter over LocalAuditKeyring.

    This adapter is not a KMS/HSM and must only be instantiated in a trusted
    backend process. It never exports private key bytes.
    """

    def __init__(self, keyring: LocalAuditKeyring):
        if not isinstance(keyring, LocalAuditKeyring):
            raise SigningProviderError("Un keyring local explicite est obligatoire.")
        self._keyring = keyring

    def sign(self, key_id: str, message: bytes) -> str:
        try:
            return self._keyring.sign(key_id, message)
        except Exception as exc:
            raise SigningProviderError("Le fournisseur de signature a refusé l'opération.") from exc

    def verify(self, key_id: str, message: bytes, signature_hex: str) -> bool:
        try:
            return self._keyring.verify(key_id, message, signature_hex) is True
        except Exception as exc:
            raise SigningProviderError("Le fournisseur de vérification est indisponible.") from exc
