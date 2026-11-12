"""Export and verify checkpoints intended for an independently controlled store.

This module does not persist checkpoints or provide external tamper resistance.
The caller must publish and retrieve these records through a separately
permissioned append-only service.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .audit import AuditError, GENESIS_HASH, read_events

CHECKPOINT_SCHEMA_VERSION = 1
CHECKPOINT_FIELDS = {"schema_version", "sequence", "head_hash"}


def build_checkpoint(path: Path) -> dict[str, Any]:
    """Return the current journal sequence and head hash for external publication."""
    events = read_events(Path(path))
    return {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "sequence": len(events),
        "head_hash": events[-1]["event_hash"] if events else GENESIS_HASH,
    }


def verify_checkpoint(path: Path, checkpoint: dict[str, Any]) -> int:
    """Verify an externally retrieved checkpoint; return the unanchored suffix length.

    A return value greater than zero means local events exist after the last
    published checkpoint. It is not evidence that those events were externally
    anchored. A missing or rolled-back local prefix raises AuditError.
    """
    if not isinstance(checkpoint, dict) or set(checkpoint) != CHECKPOINT_FIELDS:
        raise AuditError("Format de checkpoint invalide.")
    version = checkpoint["schema_version"]
    sequence = checkpoint["sequence"]
    head_hash = checkpoint["head_hash"]
    if type(version) is not int or version != CHECKPOINT_SCHEMA_VERSION:
        raise AuditError("Version de checkpoint non prise en charge.")
    if type(sequence) is not int or sequence < 0:
        raise AuditError("Séquence de checkpoint invalide.")
    if not isinstance(head_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", head_hash):
        raise AuditError("Hash de checkpoint invalide.")

    events = read_events(Path(path))
    if sequence > len(events):
        raise AuditError("Le journal local est antérieur au checkpoint externe.")
    local_hash = events[sequence - 1]["event_hash"] if sequence else GENESIS_HASH
    if local_hash != head_hash:
        raise AuditError("Le préfixe local ne correspond pas au checkpoint externe.")
    return len(events) - sequence


def verify_checkpoint_transition(
    previous: dict[str, Any], current: dict[str, Any]
) -> None:
    """Reject checkpoint rollback or equivocation between consecutive publications.

    The external store must call this while enforcing an atomic, append-only
    update. This local helper cannot prevent concurrent writers or authenticate
    either checkpoint.
    """
    _validate_checkpoint_shape(previous)
    _validate_checkpoint_shape(current)
    if current["sequence"] < previous["sequence"]:
        raise AuditError("Régression de séquence du checkpoint externe.")
    if current["sequence"] == previous["sequence"] and current["head_hash"] != previous["head_hash"]:
        raise AuditError("Deux hashes différents pour la même séquence de checkpoint.")


def _validate_checkpoint_shape(checkpoint: dict[str, Any]) -> None:
    if not isinstance(checkpoint, dict) or set(checkpoint) != CHECKPOINT_FIELDS:
        raise AuditError("Format de checkpoint invalide.")
    if type(checkpoint["schema_version"]) is not int or checkpoint["schema_version"] != CHECKPOINT_SCHEMA_VERSION:
        raise AuditError("Version de checkpoint non prise en charge.")
    if type(checkpoint["sequence"]) is not int or checkpoint["sequence"] < 0:
        raise AuditError("Séquence de checkpoint invalide.")
    if not isinstance(checkpoint["head_hash"], str) or not re.fullmatch(r"[0-9a-f]{64}", checkpoint["head_hash"]):
        raise AuditError("Hash de checkpoint invalide.")
