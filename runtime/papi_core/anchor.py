"""Protocole d'ancrage externe fournisseur-neutre pour checkpoints d'audit.

Le module ne configure aucun fournisseur. Un adaptateur doit fournir des écritures
immutables et une mise à jour compare-and-swap du pointeur de tête.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
CHECKPOINT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
CHECKPOINT_FIELDS = {
    "version", "checkpoint_id", "sequence", "audit_head",
    "previous_checkpoint_id", "created_at", "digest",
}


class AnchorError(RuntimeError):
    """Erreur d'intégrité ou de cohérence de l'ancrage."""


class AnchorUnavailable(AnchorError):
    """Le stockage d'ancrage est temporairement inaccessible."""


class AnchorIntegrityError(AnchorError):
    """Un checkpoint est absent, altéré ou mal formé."""


class AnchorConflict(AnchorError):
    """Une écriture concurrente ou une transition non autorisée a été détectée."""


class AnchorStore(Protocol):
    """Contrat minimal à implémenter par un adaptateur externe."""

    def get_head(self) -> str | None: ...
    def get_checkpoint(self, checkpoint_id: str) -> bytes | None: ...
    def put_checkpoint(self, checkpoint_id: str, payload: bytes) -> None:
        """Écriture immuable ; même clé et mêmes octets doivent être idempotents."""
        ...
    def compare_and_swap_head(self, expected: str | None, replacement: str) -> bool:
        """Remplace la tête uniquement si elle correspond à expected."""
        ...


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _digest(value: dict[str, Any]) -> str:
    body = {key: child for key, child in value.items() if key != "digest"}
    return hashlib.sha256(_canonical(body)).hexdigest()


def _parse_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    except ValueError:
        return False


class AnchorClient:
    """Client de checkpoints indépendant de tout fournisseur de stockage."""

    def __init__(self, store: AnchorStore):
        self.store = store

    @staticmethod
    def _call(operation, *args):
        try:
            return operation(*args)
        except AnchorError:
            raise
        except OSError as exc:
            raise AnchorUnavailable("Stockage d'ancrage indisponible ; état à réconcilier.") from exc

    @staticmethod
    def _decode(checkpoint_id: str, payload: bytes) -> dict[str, Any]:
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError) as exc:
            raise AnchorIntegrityError("Checkpoint absent ou JSON invalide.") from exc
        if not isinstance(value, dict) or set(value) != CHECKPOINT_FIELDS:
            raise AnchorIntegrityError("Structure de checkpoint invalide.")
        version = value.get("version")
        if (
            isinstance(version, bool) or not isinstance(version, int) or version != 1
            or not isinstance(checkpoint_id, str) or not CHECKPOINT_ID_RE.fullmatch(checkpoint_id)
            or value.get("checkpoint_id") != checkpoint_id
        ):
            raise AnchorIntegrityError("Version ou identifiant de checkpoint incohérent.")
        sequence = value.get("sequence")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
            raise AnchorIntegrityError("Séquence de checkpoint invalide.")
        if not isinstance(value.get("audit_head"), str) or not SHA256_RE.fullmatch(value["audit_head"]):
            raise AnchorIntegrityError("audit_head doit être un SHA-256.")
        previous = value.get("previous_checkpoint_id")
        if previous is not None and (
            not isinstance(previous, str) or not CHECKPOINT_ID_RE.fullmatch(previous)
        ):
            raise AnchorIntegrityError("previous_checkpoint_id invalide.")
        if not _parse_timestamp(value.get("created_at")):
            raise AnchorIntegrityError("created_at doit être une date ISO 8601 avec fuseau.")
        if not isinstance(value.get("digest"), str) or not SHA256_RE.fullmatch(value["digest"]):
            raise AnchorIntegrityError("digest doit être un SHA-256.")
        try:
            actual_digest = _digest(value)
        except (TypeError, ValueError) as exc:
            raise AnchorIntegrityError("Checkpoint non canonique ou contenant une valeur invalide.") from exc
        if actual_digest != value["digest"]:
            raise AnchorIntegrityError("Le hash cryptographique du checkpoint ne correspond pas.")
        return value

    def verify_checkpoint(self, checkpoint_id: str) -> dict[str, Any]:
        if not isinstance(checkpoint_id, str) or not CHECKPOINT_ID_RE.fullmatch(checkpoint_id):
            raise AnchorIntegrityError("Identifiant de checkpoint invalide.")
        payload = self._call(self.store.get_checkpoint, checkpoint_id)
        if payload is None:
            raise AnchorIntegrityError(f"Checkpoint supprimé ou introuvable : {checkpoint_id}.")
        if not isinstance(payload, bytes):
            raise AnchorIntegrityError("Le stockage doit retourner les octets du checkpoint.")
        return self._decode(checkpoint_id, payload)

    def verify_chain(self, head_id: str | None = None) -> list[dict[str, Any]]:
        """Retourne la chaîne vérifiée de l'ancienne racine vers la tête."""
        current = self._call(self.store.get_head) if head_id is None else head_id
        reverse_chain: list[dict[str, Any]] = []
        seen: set[str] = set()
        child_sequence: int | None = None
        while current is not None:
            if not isinstance(current, str) or not CHECKPOINT_ID_RE.fullmatch(current):
                raise AnchorIntegrityError("Pointeur de tête ou parent de checkpoint invalide.")
            if current in seen:
                raise AnchorIntegrityError("Cycle détecté dans la chaîne des checkpoints.")
            seen.add(current)
            checkpoint = self.verify_checkpoint(current)
            if child_sequence is not None and checkpoint["sequence"] >= child_sequence:
                raise AnchorIntegrityError("Les séquences de checkpoints ne sont pas monotones.")
            reverse_chain.append(checkpoint)
            child_sequence = checkpoint["sequence"]
            current = checkpoint["previous_checkpoint_id"]
        reverse_chain.reverse()
        return reverse_chain

    def publish_checkpoint(
        self, *, audit_head: str, sequence: int, checkpoint_id: str | None = None
    ) -> dict[str, Any]:
        """Publie un checkpoint ; réutiliser checkpoint_id après une réponse réseau ambiguë."""
        if not isinstance(audit_head, str) or not SHA256_RE.fullmatch(audit_head):
            raise AnchorError("audit_head doit être un SHA-256 hexadécimal.")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
            raise AnchorError("sequence doit être un entier positif.")
        identifier = str(uuid.uuid4()) if checkpoint_id is None else checkpoint_id
        if not isinstance(identifier, str) or not CHECKPOINT_ID_RE.fullmatch(identifier):
            raise AnchorError("checkpoint_id invalide.")

        head = self._call(self.store.get_head)
        existing_payload = self._call(self.store.get_checkpoint, identifier)
        if existing_payload is not None:
            existing = self._decode(identifier, existing_payload)
            if existing["audit_head"] != audit_head or existing["sequence"] != sequence:
                raise AnchorConflict("checkpoint_id déjà utilisé avec un contenu différent.")
            if head == identifier:
                return existing
            if existing["previous_checkpoint_id"] != head:
                raise AnchorConflict("Le checkpoint existant ne prolonge plus la tête actuelle.")
            if head is not None:
                previous = self.verify_checkpoint(head)
                if sequence <= previous["sequence"]:
                    raise AnchorConflict("La séquence doit être supérieure à celle de la tête.")
            if not self._call(self.store.compare_and_swap_head, head, identifier):
                raise AnchorConflict("La tête d'ancrage a changé pendant la reprise.")
            return existing

        if head is not None:
            previous = self.verify_checkpoint(head)
            if sequence <= previous["sequence"]:
                raise AnchorConflict("La séquence doit être supérieure à celle de la tête.")

        body = {
            "version": 1, "checkpoint_id": identifier, "sequence": sequence,
            "audit_head": audit_head, "previous_checkpoint_id": head,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }
        checkpoint = {**body, "digest": _digest(body)}
        payload = _canonical(checkpoint)
        self._call(self.store.put_checkpoint, identifier, payload)
        if not self._call(self.store.compare_and_swap_head, head, identifier):
            raise AnchorConflict("Une publication concurrente a modifié la tête d'ancrage.")
        return checkpoint

    def rollback(self, target_checkpoint_id: str) -> dict[str, Any]:
        """Déplace la tête vers un ancêtre vérifié sans supprimer les checkpoints ultérieurs."""
        chain = self.verify_chain()
        if not chain or target_checkpoint_id not in {item["checkpoint_id"] for item in chain}:
            raise AnchorConflict("Le rollback doit viser un checkpoint ancêtre vérifié.")
        current = chain[-1]["checkpoint_id"]
        if current == target_checkpoint_id:
            return chain[-1]
        if not self._call(self.store.compare_and_swap_head, current, target_checkpoint_id):
            raise AnchorConflict("La tête a changé pendant le rollback.")
        return self.verify_checkpoint(target_checkpoint_id)
