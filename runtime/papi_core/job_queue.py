"""Interface contrôlée vers la file persistante Supabase PAPI.

Ces méthodes réservent et suivent des jobs. Elles ne lancent aucun handler.
L'appelant doit authentifier le worker avant toute opération.
"""
from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from .storage import StoreError, SupabaseStore


class SupabaseJobQueue:
    """Client minimal de la file atomique PostgreSQL."""

    def __init__(self, store: SupabaseStore):
        if not isinstance(store, SupabaseStore):
            raise StoreError("Un SupabaseStore valide est obligatoire.")
        self.store = store

    @staticmethod
    def _text(value: Any, field: str, maximum: int = 120) -> str:
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            raise StoreError(f"{field} invalide.")
        return value.strip()

    @staticmethod
    def _token(value: str) -> str:
        try:
            return str(UUID(value))
        except (ValueError, TypeError, AttributeError) as exc:
            raise StoreError("Le lease_token doit être un UUID valide.") from exc

    @staticmethod
    def _duration(seconds: int) -> int:
        if isinstance(seconds, bool) or not isinstance(seconds, int) or not 15 <= seconds <= 900:
            raise StoreError("La durée du bail doit être comprise entre 15 et 900 secondes.")
        return seconds

    def enqueue(
        self, *, job_id: str, task_id: str, handler: str, payload: dict[str, Any],
        idempotency_key: str, agent_identity: dict[str, Any] | None = None,
        max_attempts: int = 5,
    ) -> dict[str, Any]:
        job_id = self._text(job_id, "job_id")
        task_id = self._text(task_id, "task_id")
        handler = self._text(handler, "handler", 100)
        idempotency_key = self._text(idempotency_key, "idempotency_key", 200)
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", handler):
            raise StoreError("Nom de handler invalide.")
        if not isinstance(payload, dict) or (agent_identity is not None and not isinstance(agent_identity, dict)):
            raise StoreError("payload et agent_identity doivent être des objets JSON.")
        if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or not 1 <= max_attempts <= 10:
            raise StoreError("max_attempts doit être compris entre 1 et 10.")
        row = {
            "id": job_id, "task_id": task_id, "handler": handler,
            "payload": payload, "agent_identity": agent_identity,
            "idempotency_key": idempotency_key, "max_attempts": max_attempts,
        }
        rows = self.store._request("POST", "papi_jobs", row, prefer="return=representation")
        if not isinstance(rows, list) or len(rows) != 1 or rows[0].get("id") != job_id:
            raise StoreError("Insertion du job non confirmée.")
        return rows[0]

    def claim(self, *, worker_id: str, lease_token: str, lease_seconds: int = 120) -> dict[str, Any] | None:
        worker_id = self._text(worker_id, "worker_id")
        lease_token = self._token(lease_token)
        lease_seconds = self._duration(lease_seconds)
        result = self.store._request("POST", "rpc/papi_claim_job", {
            "p_worker_id": worker_id, "p_lease_token": lease_token,
            "p_lease_seconds": lease_seconds,
        })
        if result is None:
            return None
        required = ("id", "task_id", "handler", "payload", "attempts", "lease_token", "lease_until")
        if not isinstance(result, dict) or any(key not in result for key in required):
            raise StoreError("Réponse de réservation Supabase invalide.")
        if result.get("lease_token") != lease_token or not isinstance(result.get("payload"), dict):
            raise StoreError("Jeton ou charge utile de réservation incohérent.")
        if isinstance(result.get("attempts"), bool) or not isinstance(result.get("attempts"), int) or result["attempts"] < 1:
            raise StoreError("Compteur de tentatives invalide.")
        return result

    def heartbeat(self, *, job_id: str, worker_id: str, lease_token: str, lease_seconds: int = 120) -> bool:
        result = self.store._request("POST", "rpc/papi_heartbeat_job", {
            "p_job_id": self._text(job_id, "job_id"),
            "p_worker_id": self._text(worker_id, "worker_id"),
            "p_lease_token": self._token(lease_token),
            "p_lease_seconds": self._duration(lease_seconds),
        })
        if not isinstance(result, bool):
            raise StoreError("Réponse heartbeat invalide.")
        return result

    def complete(
        self, *, job_id: str, worker_id: str, lease_token: str,
        result: dict[str, Any] | None = None,
    ) -> bool:
        if result is not None and not isinstance(result, dict):
            raise StoreError("Le résultat du job doit être un objet JSON.")
        completed = self.store._request("POST", "rpc/papi_complete_job", {
            "p_job_id": self._text(job_id, "job_id"),
            "p_worker_id": self._text(worker_id, "worker_id"),
            "p_lease_token": self._token(lease_token),
            "p_result": result or {},
        })
        if not isinstance(completed, bool):
            raise StoreError("Réponse de clôture invalide.")
        return completed

    def fail(self, *, job_id: str, worker_id: str, lease_token: str, error_code: str) -> str:
        if not isinstance(error_code, str) or not re.fullmatch(r"[a-z0-9_]{1,80}", error_code):
            raise StoreError("error_code doit respecter le format [a-z0-9_]{1,80}.")
        status = self.store._request("POST", "rpc/papi_fail_job", {
            "p_job_id": self._text(job_id, "job_id"),
            "p_worker_id": self._text(worker_id, "worker_id"),
            "p_lease_token": self._token(lease_token),
            "p_error_code": error_code,
        })
        if status not in {"retry", "failed"}:
            raise StoreError("Statut de reprise inattendu.")
        return status
