"""Worker à un seul job ; authentification requise avant tout handler."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .authz import AccessDenied, authorize_authenticated_agent
from .execution_queue import ExecutionQueue, QueueError
from .handler_registry import HandlerRegistry, PermissionError as HandlerPermissionError, execute_authorized_job
from .identity import DEFAULT_KEY_DIR, DEFAULT_REPLAY_DB
from .identity_ed25519 import DEFAULT_PUBLIC_REGISTRY
from .storage import StoreError

class WorkerError(RuntimeError):
    """Erreur contrôlée du worker."""

PERMISSION_BY_CLASS = {
    "read_only": "read_reports",
    "internal_write": "update_internal_state",
    "external_communication": "send_message",
    "financial": "make_payment",
    "legal": "accept_legal_commitments",
}

class PapiWorker:
    def __init__(self, *, queue: ExecutionQueue, registry: HandlerRegistry,
                 policy: dict[str, Any], worker_id: str,
                 key_dir: Path = DEFAULT_KEY_DIR, replay_db: Path = DEFAULT_REPLAY_DB,
                 public_registry: Path = DEFAULT_PUBLIC_REGISTRY,
                 shared_identity_verifier: Any | None = None) -> None:
        if not isinstance(worker_id, str) or not worker_id.strip():
            raise WorkerError("Identifiant worker obligatoire.")
        if not isinstance(policy, dict):
            raise WorkerError("Politique invalide.")
        self.queue, self.registry, self.policy, self.worker_id = queue, registry, policy, worker_id
        self.key_dir, self.replay_db, self.public_registry = key_dir, replay_db, public_registry
        self.shared_identity_verifier = shared_identity_verifier

    def run_once(self) -> dict[str, Any]:
        """Traite au maximum un travail ; aucune réservation si l'exécution est désactivée."""
        if self.policy.get("execution_enabled") is not True:
            return {"status": "disabled", "claimed": False}
        job = self.queue.claim(worker_id=self.worker_id)
        if job is None:
            return {"status": "idle", "claimed": False}
        job_id, lease_token = job.get("id"), job.get("lease_token")
        if not isinstance(job_id, str) or not isinstance(lease_token, str):
            return {"status": "invalid_claim", "claimed": True}
        try:
            task_id = job.get("task_id")
            if not isinstance(task_id, str) or not task_id:
                raise WorkerError("task_missing")
            stored = self.queue.store.get_task(task_id)
            if not isinstance(stored, dict) or not isinstance(stored.get("task"), dict):
                raise WorkerError("task_missing")
            task = stored["task"]
            handler = job.get("handler")
            spec = self.registry.get(handler)
            permission = PERMISSION_BY_CLASS.get(spec.action_class)
            if permission is None:
                raise AccessDenied("Classe de permission non prise en charge.")
            agent_id = task.get("owner_agent")
            authorization = authorize_authenticated_agent(
                agent_id, permission, job.get("agent_identity"),
                task_id=task_id, handler=handler, policy=self.policy,
                key_dir=self.key_dir, replay_db=self.replay_db,
                public_registry=self.public_registry,
                shared_identity_verifier=self.shared_identity_verifier,
            )
            result = execute_authorized_job(job, task, self.policy, self.registry,
                context={"worker_id": self.worker_id, "task_id": task_id,
                         "authenticated_agent_id": agent_id,
                         "authenticated_principal": authorization["principal"]})
            if not self.queue.complete(job_id=job_id, worker_id=self.worker_id, lease_token=lease_token, result=result):
                return {"status": "lease_lost", "claimed": True, "job_id": job_id}
            return {"status": "completed", "claimed": True, "job_id": job_id}
        except AccessDenied:
            self.queue.fail(job_id=job_id, worker_id=self.worker_id, lease_token=lease_token, error_code="authentication_failed")
            return {"status": "blocked", "claimed": True, "job_id": job_id}
        except HandlerPermissionError:
            self.queue.fail(job_id=job_id, worker_id=self.worker_id, lease_token=lease_token, error_code="permission_denied")
            return {"status": "blocked", "claimed": True, "job_id": job_id}
        except (WorkerError, StoreError, QueueError):
            self.queue.fail(job_id=job_id, worker_id=self.worker_id, lease_token=lease_token, error_code="worker_validation_error")
            return {"status": "failed", "claimed": True, "job_id": job_id}
        except Exception:
            self.queue.fail(job_id=job_id, worker_id=self.worker_id, lease_token=lease_token, error_code="handler_error")
            return {"status": "failed", "claimed": True, "job_id": job_id}
