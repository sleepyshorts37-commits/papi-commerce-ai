"""File de travaux avec baux, idempotence et preuve d'identité de l'agent."""
from __future__ import annotations
import math
import re
from typing import Any
from uuid import uuid4
from .retry_policy import RetryPolicyError, decide_retry
from .storage import SupabaseStore

class QueueError(RuntimeError):
    """Erreur de file ou de propriété d'un travail."""

class ExecutionQueue:
    """Client de file ; ne lance aucun handler."""
    def __init__(self, store: SupabaseStore):
        self.store = store

    def enqueue(self, *, job_id: str, task_id: str, handler: str, payload: dict[str, Any],
                idempotency_key: str, agent_identity: dict[str, Any] | None = None) -> dict[str, Any]:
        if not all(isinstance(x, str) and x.strip() for x in (job_id, task_id, handler, idempotency_key)):
            raise QueueError("Identifiants, handler et clé d'idempotence obligatoires.")
        if not isinstance(payload, dict):
            raise QueueError("Le contenu du travail doit être un objet.")
        if agent_identity is not None and not isinstance(agent_identity, dict):
            raise QueueError("La preuve d'identité doit être un objet.")
        if len(handler) > 100 or len(idempotency_key) > 160:
            raise QueueError("Handler ou clé d'idempotence trop long.")
        result = self.store._request("POST", "papi_jobs",
            {"id": job_id, "task_id": task_id, "handler": handler, "payload": payload,
             "agent_identity": agent_identity, "idempotency_key": idempotency_key,
             "status": "queued", "attempts": 0, "max_attempts": 5},
            prefer="return=representation")
        if not isinstance(result, list) or len(result) != 1:
            raise QueueError("Insertion non confirmée ; vérifier la clé d'idempotence.")
        return result[0]

    def claim(self, *, worker_id: str, lease_seconds: int = 120) -> dict[str, Any] | None:
        if not isinstance(worker_id, str) or not worker_id.strip() or len(worker_id) > 120:
            raise QueueError("Identifiant worker invalide.")
        if not isinstance(lease_seconds, int) or not 15 <= lease_seconds <= 900:
            raise QueueError("Le bail doit être compris entre 15 et 900 secondes.")
        result = self.store._request("POST", "rpc/papi_claim_job",
            {"p_worker_id": worker_id, "p_lease_token": str(uuid4()), "p_lease_seconds": lease_seconds})
        if result is None:
            return None
        if (not isinstance(result, dict) or not result.get("id")
                or not result.get("lease_token")
                or type(result.get("attempts")) is not int
                or type(result.get("max_attempts")) is not int
                or result["attempts"] < 1
                or result["max_attempts"] < result["attempts"]
                or result["max_attempts"] > 10):
            raise QueueError("Réponse de réservation invalide.")
        return result

    def renew(self, *, job_id: str, worker_id: str, lease_token: str,
              lease_seconds: int = 900) -> bool:
        """Prolonge uniquement un bail encore valide détenu par ce worker."""
        if not all(isinstance(x, str) and x.strip() for x in (job_id, worker_id, lease_token)):
            raise QueueError("Identifiants de réservation obligatoires.")
        if len(worker_id) > 120:
            raise QueueError("Identifiant worker trop long.")
        if type(lease_seconds) is not int or not 15 <= lease_seconds <= 900:
            raise QueueError("Le bail doit être un entier compris entre 15 et 900 secondes.")
        response = self.store._request("POST", "rpc/papi_renew_job_lease",
            {"p_job_id": job_id, "p_worker_id": worker_id,
             "p_lease_token": lease_token, "p_lease_seconds": lease_seconds})
        return response is True

    def complete(self, *, job_id: str, worker_id: str, lease_token: str,
                 result: dict[str, Any] | None = None) -> bool:
        if not all(isinstance(x, str) and x.strip() for x in (job_id, worker_id, lease_token)):
            raise QueueError("Identifiants de réservation obligatoires.")
        if result is not None and not isinstance(result, dict):
            raise QueueError("Le résultat doit être un objet.")
        response = self.store._request("POST", "rpc/papi_complete_job",
            {"p_job_id": job_id, "p_worker_id": worker_id, "p_lease_token": lease_token, "p_result": result or {}})
        return response is True

    def fail(self, *, job_id: str, worker_id: str, lease_token: str, error_code: str,
             attempt: int = 1, max_attempts: int = 5, jitter_sample: float = 0.5) -> str:
        if not all(isinstance(x, str) and x.strip() for x in (job_id, worker_id, lease_token, error_code)):
            raise QueueError("Identifiants et code d'erreur obligatoires.")
        if not re.fullmatch(r"[a-z0-9_]{1,80}", error_code):
            raise QueueError("Code d'erreur invalide ou potentiellement sensible.")
        try:
            decision = decide_retry(
                error_code=error_code, attempt=attempt, max_attempts=max_attempts,
                base_delay_seconds=15, max_delay_seconds=3600,
                jitter_fraction=0.2, jitter_sample=jitter_sample,
            )
        except RetryPolicyError as exc:
            raise QueueError("Paramètres de reprise invalides.") from exc
        retry_allowed = decision.retry
        retry_delay_seconds = math.ceil(decision.delay_seconds) if retry_allowed else 0
        response = self.store._request("POST", "rpc/papi_fail_job",
            {"p_job_id": job_id, "p_worker_id": worker_id, "p_lease_token": lease_token,
             "p_error_code": error_code, "p_retry_allowed": retry_allowed,
             "p_retry_delay_seconds": retry_delay_seconds})
        if response not in {"retry", "failed"}:
            raise QueueError("Réponse de reprise invalide.")
        return response
