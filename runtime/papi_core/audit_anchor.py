"""Provider-neutral publication contract for signed audit checkpoints.

This module contains no network client, credentials, key storage, or production
store. A deployment must inject an independently administered CheckpointStore
and a signature verifier backed by a managed signing-key boundary.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable, Protocol

from .audit import AuditError
from .audit_checkpoint import (
    build_checkpoint,
    verify_checkpoint,
    verify_checkpoint_transition,
)

RECORD_SCHEMA_VERSION = 1
RECORD_FIELDS = {
    "schema_version",
    "journal_id",
    "checkpoint",
    "previous_record_digest",
    "key_id",
    "signature",
}
DIGEST_RE = re.compile(r"[0-9a-f]{64}")


class CheckpointAnchorError(AuditError):
    """External checkpoint record or publication contract is invalid."""


class CheckpointConflict(CheckpointAnchorError):
    """The external latest pointer changed before compare-and-swap."""


class CheckpointStore(Protocol):
    """Minimum storage contract required from an external provider."""

    def get_latest(self, journal_id: str) -> str | None:
        """Return the latest immutable record digest, or None at genesis."""

    def get_record(self, record_digest: str) -> bytes | None:
        """Return exact canonical bytes for an immutable record."""

    def put_record(self, record_digest: str, canonical_record: bytes) -> None:
        """Insert immutable bytes; identical retries must be idempotent."""

    def compare_and_swap_latest(
        self, journal_id: str, expected_digest: str | None, new_digest: str
    ) -> bool:
        """Atomically advance latest only if it still equals expected_digest."""


SignatureVerifier = Callable[[str, bytes, str], bool]


def canonical_record_bytes(record: dict[str, Any]) -> bytes:
    """Serialize a record deterministically; callers must sign unsigned bytes."""
    try:
        return json.dumps(
            record, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CheckpointAnchorError("Enregistrement de checkpoint non sérialisable.") from exc


def _unsigned_payload(record: dict[str, Any]) -> bytes:
    return canonical_record_bytes({key: value for key, value in record.items() if key != "signature"})


def _record_digest(canonical_record: bytes) -> str:
    return hashlib.sha256(canonical_record).hexdigest()


def _validate_record(
    record: Any,
    *,
    journal_id: str,
    expected_digest: str | None,
    verifier: SignatureVerifier,
) -> dict[str, Any]:
    if not isinstance(record, dict) or set(record) != RECORD_FIELDS:
        raise CheckpointAnchorError("Format d'enregistrement externe invalide.")
    if type(record["schema_version"]) is not int or record["schema_version"] != RECORD_SCHEMA_VERSION:
        raise CheckpointAnchorError("Version d'enregistrement externe non prise en charge.")
    if record["journal_id"] != journal_id or not isinstance(journal_id, str) or not journal_id.strip():
        raise CheckpointAnchorError("Identifiant de journal externe incorrect.")
    if not isinstance(record["key_id"], str) or not record["key_id"].strip():
        raise CheckpointAnchorError("Identifiant de clé de signature invalide.")
    if not isinstance(record["signature"], str) or not record["signature"]:
        raise CheckpointAnchorError("Signature externe absente.")
    previous = record["previous_record_digest"]
    if previous is not None and (not isinstance(previous, str) or not DIGEST_RE.fullmatch(previous)):
        raise CheckpointAnchorError("Lien vers l'enregistrement précédent invalide.")
    try:
        verify_checkpoint_transition(record["checkpoint"], record["checkpoint"])
    except (AttributeError, TypeError, AuditError) as exc:
        raise CheckpointAnchorError("Checkpoint contenu dans l'enregistrement invalide.") from exc
    if expected_digest is not None and previous != expected_digest:
        raise CheckpointAnchorError("La chaîne des enregistrements externes est rompue.")
    try:
        valid_signature = verifier(record["key_id"], _unsigned_payload(record), record["signature"])
    except Exception as exc:
        raise CheckpointAnchorError("Échec du vérificateur de signature externe.") from exc
    if valid_signature is not True:
        raise CheckpointAnchorError("Signature externe invalide.")
    canonical = canonical_record_bytes(record)
    return record


def publish_checkpoint_record(
    *,
    journal_path: Any,
    journal_id: str,
    record: dict[str, Any],
    store: CheckpointStore,
    verify_signature: SignatureVerifier,
) -> str:
    """Publish one signed checkpoint with immutable insert and atomic CAS.

    The signer is intentionally not implemented here. The caller must create
    the signed record using a key held outside the worker. CAS conflicts are
    surfaced so the caller can reload the latest record and restart validation.
    """
    if not isinstance(journal_id, str) or not journal_id.strip():
        raise CheckpointAnchorError("Identifiant de journal obligatoire.")
    if not isinstance(record, dict):
        raise CheckpointAnchorError("Enregistrement de checkpoint invalide.")
    latest_digest = store.get_latest(journal_id)
    previous_record = None
    if latest_digest is not None:
        if not isinstance(latest_digest, str) or not DIGEST_RE.fullmatch(latest_digest):
            raise CheckpointAnchorError("Pointeur externe latest invalide.")
        previous_bytes = store.get_record(latest_digest)
        if not isinstance(previous_bytes, bytes):
            raise CheckpointAnchorError("Enregistrement externe précédent introuvable.")
        try:
            previous_record = json.loads(previous_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CheckpointAnchorError("Enregistrement externe précédent illisible.") from exc
        cursor = latest_digest
        seen_digests: set[str] = set()
        newer_sequence: int | None = None
        while cursor is not None:
            if cursor in seen_digests:
                raise CheckpointAnchorError("Cycle dans la chaîne des checkpoints externes.")
            seen_digests.add(cursor)
            raw_record = store.get_record(cursor)
            if not isinstance(raw_record, bytes):
                raise CheckpointAnchorError("Enregistrement externe de la chaîne introuvable.")
            try:
                chain_record = json.loads(raw_record.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise CheckpointAnchorError("Enregistrement externe de la chaîne illisible.") from exc
            _validate_record(
                chain_record, journal_id=journal_id,
                expected_digest=None, verifier=verify_signature,
            )
            canonical_chain_record = canonical_record_bytes(chain_record)
            if raw_record != canonical_chain_record:
                raise CheckpointAnchorError("Enregistrement externe non canonique.")
            if _record_digest(raw_record) != cursor:
                raise CheckpointAnchorError("Empreinte d'un checkpoint externe incorrecte.")
            sequence = chain_record["checkpoint"]["sequence"]
            if newer_sequence is not None and sequence >= newer_sequence:
                raise CheckpointAnchorError("Les séquences de la chaîne externe ne progressent pas.")
            newer_sequence = sequence
            cursor = chain_record["previous_record_digest"]
            if cursor is None:
                previous_record = chain_record
            elif cursor not in seen_digests:
                # The next iteration verifies the referenced immutable predecessor.
                pass
        previous_record = json.loads(store.get_record(latest_digest).decode("utf-8"))
        try:
            verify_checkpoint(journal_path, previous_record["checkpoint"])
        except AuditError as exc:
            raise CheckpointAnchorError("Le journal local ne contient pas le préfixe déjà ancré.") from exc

    candidate = build_checkpoint(journal_path)
    if record.get("checkpoint") != candidate:
        raise CheckpointAnchorError("Le checkpoint signé ne correspond pas au journal local vérifié.")
    expected_previous = latest_digest
    if record.get("previous_record_digest") != expected_previous:
        raise CheckpointAnchorError("Le nouveau checkpoint ne référence pas le dernier enregistrement.")
    if expected_previous is None and record.get("previous_record_digest") is not None:
        raise CheckpointAnchorError("Le premier checkpoint doit référencer genesis.")
    _validate_record(
        record, journal_id=journal_id,
        expected_digest=expected_previous, verifier=verify_signature,
    )
    if previous_record is not None:
        verify_checkpoint_transition(previous_record["checkpoint"], record["checkpoint"])
        if record["checkpoint"]["sequence"] <= previous_record["checkpoint"]["sequence"]:
            raise CheckpointAnchorError("La séquence doit progresser strictement.")
    canonical = canonical_record_bytes(record)
    digest = _record_digest(canonical)
    store.put_record(digest, canonical)
    if store.compare_and_swap_latest(journal_id, expected_previous, digest) is not True:
        raise CheckpointConflict("Conflit CAS: recharger le dernier checkpoint avant toute reprise.")
    return digest
