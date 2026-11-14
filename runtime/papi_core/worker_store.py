"""Deterministic event envelopes and explicit Supabase worker-store adapter.

No client is created implicitly. Network access only occurs when a caller injects
an already configured server-side store and explicitly invokes a store method.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import re
from typing import Any

DOMAINS = {"platform_candidate", "human_handoff", "profitability_result"}
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")
SENSITIVE_TEXT = re.compile(
    r"\b(?:password|passwd|otp|one[- ]time code|private key|seed phrase|recovery phrase|access token|refresh token)\s*[:=]",
    re.IGNORECASE,
)
SENSITIVE_KEYS = {
    "password", "passwd", "otp", "one_time_code", "verification_code",
    "private_key", "secret_key", "seed_phrase", "recovery_phrase",
    "card_number", "cvv", "cvc", "access_token", "refresh_token",
    "service_role_key", "api_key", "authorization",
}


class WorkerStoreError(ValueError):
    """Invalid event envelope or unsafe persistence payload."""


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or not IDENTIFIER.fullmatch(value.strip()):
        raise WorkerStoreError(f"{field} est obligatoire et doit respecter le format autorisé.")
    return value.strip()


def _reject_secrets(value: Any, path: str = "payload") -> None:
    if isinstance(value, str) and SENSITIVE_TEXT.search(value):
        raise WorkerStoreError(f"Contenu sensible détecté dans {path}.")
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().casefold().replace("-", "_")
            if normalized in SENSITIVE_KEYS:
                raise WorkerStoreError(f"Champ sensible interdit dans {path}.{key}.")
            _reject_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secrets(child, f"{path}[{index}]")


def build_worker_sync_event(
    *, domain: str, record_id: str, source_event_id: str, event_type: str,
    actor: str, occurred_at: str, payload: dict[str, Any],
) -> dict[str, Any]:
    """Build a stable envelope: retries of the same source event get the same IDs."""
    if domain not in DOMAINS:
        raise WorkerStoreError("Domaine de synchronisation inconnu.")
    record = _required_text(record_id, "record_id")
    source_id = _required_text(source_event_id, "source_event_id")
    event_name = _required_text(event_type, "event_type")
    actor_id = _required_text(actor, "actor")
    if not isinstance(payload, dict):
        raise WorkerStoreError("payload doit être un objet JSON.")
    _reject_secrets(payload)
    try:
        canonical_payload = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        safe_payload = json.loads(canonical_payload)
    except (TypeError, ValueError) as exc:
        raise WorkerStoreError("payload doit être un objet JSON sérialisable sans NaN/Infinity.") from exc
    if not isinstance(occurred_at, str) or not occurred_at.strip():
        raise WorkerStoreError("occurred_at doit être une date ISO-8601 avec fuseau horaire.")
    try:
        parsed = datetime.fromisoformat(occurred_at.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise WorkerStoreError("occurred_at doit être une date ISO-8601 valide.") from exc
    if parsed.tzinfo is None:
        raise WorkerStoreError("occurred_at doit inclure un fuseau horaire.")
    timestamp = parsed.isoformat(timespec="microseconds").replace("+00:00", "Z")
    identity = f"{domain}:{record}:{source_id}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return {
        "domain": domain, "record_id": record, "source_event_id": source_id,
        "event_type": event_name, "actor": actor_id, "occurred_at": timestamp,
        "payload": safe_payload, "event_id": f"WEVT-{digest[:32].upper()}",
        "idempotency_key": digest, "persistence_performed": False,
        "network_access_performed": False,
    }


class SupabaseWorkerStore:
    """Explicit worker persistence adapter over an injected server-side SupabaseStore."""

    def __init__(self, store: Any) -> None:
        if not callable(getattr(store, "sync_worker_event", None)) or not callable(
            getattr(store, "list_worker_records", None)
        ):
            raise WorkerStoreError("Le stockage injecté ne fournit pas les opérations workers requises.")
        self.store = store

    def sync_event(self, event: dict[str, Any], *, expected_version: int) -> dict[str, Any]:
        if not isinstance(event, dict) or event.get("domain") not in DOMAINS:
            raise WorkerStoreError("Événement worker invalide.")
        if not isinstance(expected_version, int) or isinstance(expected_version, bool) or expected_version < 0:
            raise WorkerStoreError("Version attendue invalide.")
        required = {
            "record_id", "source_event_id", "event_type", "actor", "occurred_at",
            "payload", "event_id", "idempotency_key",
        }
        if not required.issubset(event):
            raise WorkerStoreError("Enveloppe worker incomplète.")
        _reject_secrets(event["payload"])
        result = self.store.sync_worker_event(event, expected_version=expected_version)
        if not isinstance(result, dict) or not isinstance(result.get("duplicate"), bool):
            raise WorkerStoreError("Réponse de synchronisation Supabase invalide.")
        return result

    def load_worker_inputs(self, *, limit_per_domain: int = 500) -> dict[str, list[dict[str, Any]]]:
        if not isinstance(limit_per_domain, int) or isinstance(limit_per_domain, bool) or not 1 <= limit_per_domain <= 1000:
            raise WorkerStoreError("Limite de lecture invalide.")
        return {
            "platform_candidates": self.store.list_worker_records("platform_candidate", limit=limit_per_domain),
            "handoffs": self.store.list_worker_records("human_handoff", limit=limit_per_domain),
            "profitability_results": self.store.list_worker_records("profitability_result", limit=limit_per_domain),
        }
