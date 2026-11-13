"""Supabase/PostgREST adapter for the signed audit checkpoint store.

The caller must supply a server-side service-role credential. Never instantiate
this adapter in an agent-facing process or expose the credential to a worker.
"""
from __future__ import annotations

import hashlib
import json
from urllib.parse import quote

from .audit_anchor import (
    CheckpointStore,
    SignatureVerifier,
    validate_signed_checkpoint_record,
)
from .storage import StoreError, SupabaseStore


class SupabaseCheckpointStore(CheckpointStore):
    """Persist immutable signed records and atomically advance their journal head."""

    def __init__(self, store: SupabaseStore, *, verify_signature: SignatureVerifier):
        if not isinstance(store, SupabaseStore):
            raise StoreError("Un client Supabase serveur est obligatoire.")
        if not callable(verify_signature):
            raise StoreError("Un vérificateur de signature obligatoire est requis.")
        self.store = store
        self.verify_signature = verify_signature

    def _validate_signed_record(
        self, canonical_record: bytes, *, journal_id: str,
        expected_previous_digest: str | None = None,
    ) -> dict:
        try:
            return validate_signed_checkpoint_record(
                canonical_record,
                journal_id=journal_id,
                verify_signature=self.verify_signature,
                expected_previous_digest=expected_previous_digest,
            )
        except Exception as exc:
            raise StoreError("Enregistrement signé refusé par l'adaptateur.") from exc

    def get_latest(self, journal_id: str) -> str | None:
        rows = self.store.request(
            "GET",
            "papi_audit_anchor_heads"
            f"?journal_id=eq.{quote(journal_id, safe='')}&select=latest_record_digest",
        )
        if not isinstance(rows, list):
            raise StoreError("Réponse inattendue pour le pointeur d'audit externe.")
        if not rows:
            return None
        digest = rows[0].get("latest_record_digest")
        if not isinstance(digest, str):
            raise StoreError("Pointeur d'audit externe invalide.")
        return digest

    def get_record(self, record_digest: str) -> bytes | None:
        rows = self.store.request(
            "GET",
            "papi_audit_anchor_records"
            f"?record_digest=eq.{quote(record_digest, safe='')}&select=canonical_record",
        )
        if not isinstance(rows, list):
            raise StoreError("Réponse inattendue pour l'enregistrement d'audit externe.")
        if not rows:
            return None
        canonical = rows[0].get("canonical_record")
        if not isinstance(canonical, str):
            raise StoreError("Enregistrement d'audit externe invalide.")
        encoded = canonical.encode("utf-8")
        if hashlib.sha256(encoded).hexdigest() != record_digest:
            raise StoreError("Digest de l'enregistrement récupéré incorrect.")
        return encoded

    def put_record(self, record_digest: str, canonical_record: bytes) -> None:
        if not isinstance(record_digest, str) or hashlib.sha256(canonical_record).hexdigest() != record_digest:
            raise StoreError("Digest de l'enregistrement d'audit incorrect.")
        try:
            record = json.loads(canonical_record.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StoreError("Enregistrement d'audit non lisible.") from exc
        journal_id = record.get("journal_id") if isinstance(record, dict) else None
        if not isinstance(journal_id, str) or not journal_id:
            raise StoreError("Identifiant de journal absent de l'enregistrement.")
        self._validate_signed_record(canonical_record, journal_id=journal_id)
        self.store.request(
            "POST",
            "papi_audit_anchor_records?on_conflict=journal_id,record_digest",
            {
                "journal_id": journal_id,
                "record_digest": record_digest,
                "canonical_record": canonical_record.decode("utf-8"),
            },
            prefer="resolution=ignore-duplicates,return=minimal",
        )
        stored = self.get_record(record_digest)
        if stored != canonical_record:
            raise StoreError("Le stockage externe n'a pas confirmé les octets immuables.")

    def compare_and_swap_latest(
        self, journal_id: str, expected_digest: str | None, new_digest: str
    ) -> bool:
        canonical = self.get_record(new_digest)
        if canonical is None:
            raise StoreError("Enregistrement d'audit externe introuvable.")
        self._validate_signed_record(
            canonical, journal_id=journal_id,
            expected_previous_digest=expected_digest,
        )
        result = self.store.request(
            "POST",
            "rpc/papi_advance_audit_anchor",
            {
                "p_journal_id": journal_id,
                "p_expected_digest": expected_digest,
                "p_new_digest": new_digest,
            },
        )
        if type(result) is not bool:
            raise StoreError("Réponse inattendue de l'atomicité du checkpoint externe.")
        return result
