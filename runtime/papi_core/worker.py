"""Worker à un seul job ; aucun démarrage permanent ni action externe implicite."""
from __future__ import annotations

from typing import Any

from .execution_queue import ExecutionQueue, QueueError
from .handler_registry import (
    HandlerRegistry,
    PermissionError as HandlerPermissionError,
    execute_authorized_job,
)
from .storage import StoreError


class WorkerError(RuntimeError):
    """Erreur contrôlée du worker."""


class PapiWorker:
    def __init__(
        self,
        *,
        queue: ExecutionQueue,
        registry: HandlerRegistry,
        policy: dict[str, Any],
        worker_id: str,
    ) -> None:
        if not isinstance(worker_id, str) or not worker_id.strip():
            raise WorkerError("Identifiant worker obligatoire.")
        if not isinstance(policy, dict):
            raise WorkerError("Politique invalide.")
        self.queue = queue
        self.registry = registry
        self.policy = policy
        self.worker_id = worker_id

    def run_once(self) -> dict[str, Any]:
        """Traite au maximum un travail. Si le mode est désactivé, ne réserve rien."""
        if self.policy.get("execution_enabled") is not True:
            return {"status": "disabled", "claimed": False}
        job = self.queue.claim(worker_id=self.worker_id)
        if job is None:
            return {"status": "idle", "claimed": False}
        job_id = job.get("id")
        lease_token = job.get("lease_token")
        if not isinstance(job_id, str) or not isinstance(lease_token, str):
            return {"status": "invalid_claim", "claimed": True}
        try:
            task_id = job.get("task_id")
            if not isinstance(task_id, str) or not task_id:
                raise WorkerError("task_missing")
            stored = self.queue.store.get_task(task_id)
            if not isinstance(stored, dict) or not isinstance(stored.get("task"), dict):
                raise WorkerError("task_missing")
            result = execute_authorized_job(
                job,
                stored["task"],
                self.policy,
                self.registry,
                context={"worker_id": self.worker_id, "task_id": task_id},
            )
            completed = self.queue.complete(
                job_id=job_id,
                worker_id=self.worker_id,
                lease_token=lease_token,
                result=result,
            )
            if not completed:
                return {"status": "lease_lost", "claimed": True, "job_id": job_id}
            return {"status": "completed", "claimed": True, "job_id": job_id}
        except HandlerPermissionError:
            self.queue.fail(
                job_id=job_id, worker_id=self.worker_id,
                lease_token=lease_token, error_code="permission_denied",
            )
            return {"status": "blocked", "claimed": True, "job_id": job_id}
        except (WorkerError, StoreError, QueueError):
            self.queue.fail(
                job_id=job_id, worker_id=self.worker_id,
                lease_token=lease_token, error_code="worker_validation_error",
            )
            return {"status": "failed", "claimed": True, "job_id": job_id}
        except Exception:
            self.queue.fail(
                job_id=job_id, worker_id=self.worker_id,
                lease_token=lease_token, error_code="handler_error",
            )
            return {"status": "failed", "claimed": True, "job_id": job_id}
