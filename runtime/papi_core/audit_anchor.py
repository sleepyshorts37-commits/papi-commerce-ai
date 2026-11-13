"""Protocol for publishing audit checkpoints to an independently controlled store.

No network client or provider credentials are included. A production backend must
implement compare_and_append atomically in a separately permissioned service.
"""
from __future__ import annotations

from typing import Any, Protocol

from .audit import AuditError
from .audit_checkpoint import build_checkpoint, verify_checkpoint, verify_checkpoint_transition


class AuditAnchorError(AuditError):
    """Publication or verification against an external audit anchor failed."""


class AuditAnchorBackend(Protocol):
    """Minimal contract for a separately controlled append-only witness."""

    def latest(self) -> dict[str, Any] | None:
        """Return the latest published checkpoint, or None when empty."""
        ...

    def compare_and_append(
        self,
        expected_previous: dict[str, Any] | None,
        checkpoint: dict[str, Any],
    ) -> bool:
        """Atomically append iff latest() still equals expected_previous."""
        ...


def publish_checkpoint(path: Any, backend: AuditAnchorBackend) -> bool:
    """Publish the current local head; False means it was already anchored.

    The backend must implement compare_and_append as one atomic operation.
    This helper never sends event payloads, only sequence and SHA-256 head hash.
    """
    checkpoint = build_checkpoint(path)
    previous = backend.latest()
    if previous is not None:
        verify_checkpoint_transition(previous, checkpoint)
        # Prove that the stored anchor is a prefix of this exact local chain;
        # sequence monotonicity alone would permit a fork with an unrelated hash.
        verify_checkpoint(path, previous)
        if previous == checkpoint:
            return False
    if not backend.compare_and_append(previous, checkpoint):
        raise AuditAnchorError("Conflit de publication : le checkpoint externe a changé.")
    confirmed = backend.latest()
    if confirmed != checkpoint:
        raise AuditAnchorError("Le backend n'a pas confirmé le checkpoint publié.")
    return True


def verify_against_anchor(path: Any, backend: AuditAnchorBackend) -> int:
    """Verify the local journal against the latest independently stored anchor."""
    checkpoint = backend.latest()
    if checkpoint is None:
        raise AuditAnchorError("Aucun checkpoint externe n'est disponible.")
    try:
        return verify_checkpoint(path, checkpoint)
    except AuditError as exc:
        raise AuditAnchorError(str(exc)) from exc
