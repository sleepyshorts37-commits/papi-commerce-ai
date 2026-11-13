"""Worker à un seul job ; audit lié à chaque tentative durable."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from uuid import UUID

from .audit import append_event, new_event
from .authz import AccessDenied, AuthenticatedAuthorizationDenied, authorize_authenticated_agent
from .execution_queue import ExecutionQueue, QueueError
from .handler_registry import HandlerRegistry, PermissionError as HandlerPermissionError, authorize_job, execute_authorized_job
from .identity import DEFAULT_KEY_DIR, DEFAULT_REPLAY_DB
from .identity_ed25519 import DEFAULT_PUBLIC_REGISTRY
from .storage import StoreError


class WorkerError(RuntimeError):
    """Erreur contrôlée du worker."""


class LeaseLostError(WorkerError):
    """Le worker ne détient plus le bail courant."""


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
                 shared_identity_verifier: Any | None = None,
                 audit_path: Path | None = None) -> None:
        if not isinstance(worker_id, str) or not worker_id.strip():
            raise WorkerError("Identifiant worker obligatoire.")
        if not isinstance(policy, dict):
            raise WorkerError("Politique invalide.")
        self.queue, self.registry, self.policy, self.worker_id = queue, registry, policy, worker_id
        self.key_dir, self.replay_db, self.public_registry = key_dir, replay_db, public_registry
        self.shared_identity_verifier = shared_identity_verifier
        self.audit_path = Path(audit_path) if audit_path is not None else Path.home() / ".papi" / "audit" / "events.jsonl"

    def _audit(self, *, job_id: str, task_id: str, attempt_id: str, action: str,
               actor: str, outcome: str, handler: str = "unknown") -> bool:
        """Déduplique par tentative, pas seulement par job : les retries restent distincts."""
        job_digest = hashlib.sha256(job_id.encode("utf-8")).hexdigest()
        dedupe_material = f"{job_id}:{attempt_id}:{action}"
        dedupe_id = hashlib.sha256(dedupe_material.encode("utf-8")).hexdigest()
        event = new_event(
            event_id="worker:" + dedupe_id,
            actor=actor,
            action=action,
            entity_type="job",
            entity_id=job_digest,
            details={
                "job_id": job_id[:120],
                "task_id": task_id[:120],
                "attempt_id": attempt_id,
                "worker_id": self.worker_id[:100],
                "handler": handler[:120],
                "outcome": outcome[:80],
                "dedupe_id": dedupe_id,
            },
        )
        append_event(event, self.audit_path)
        return True

    def _audit_best_effort(self, **kwargs: Any) -> None:
        try:
            self._audit(**kwargs)
        except Exception:
            return

    def _fail_job(self, *, job_id: str, task_id: str, attempt_id: str,
                  lease_token: str, error_code: str, status: str,
                  actor: str, action: str, handler: str, outcome: str) -> dict[str, Any]:
        try:
            self.queue.fail(job_id=job_id, worker_id=self.worker_id,
                            lease_token=lease_token, error_code=error_code)
        except Exception:
            self._audit_best_effort(job_id=job_id, task_id=task_id, attempt_id=attempt_id,
                action="job.failure_transition_error", actor=actor,
                handler=handler, outcome="queue_fail_error")
            return {"status": "failure_transition_error", "claimed": True, "job_id": job_id,
                    "attempt_id": attempt_id}
        self._audit_best_effort(job_id=job_id, task_id=task_id, attempt_id=attempt_id,
            action=action, actor=actor, handler=handler, outcome=outcome)
        return {"status": status, "claimed": True, "job_id": job_id, "attempt_id": attempt_id}

    def run_once(self) -> dict[str, Any]:
        """Traite au maximum un travail ; handler interdit si l'audit de démarrage échoue."""
        if self.policy.get("execution_enabled") is not True:
            return {"status": "disabled", "claimed": False}
        job = self.queue.claim(worker_id=self.worker_id)
        if job is None:
            return {"status": "idle", "claimed": False}
        job_id, lease_token, attempt_id = job.get("id"), job.get("lease_token"), job.get("attempt_id")
        if not isinstance(job_id, str) or not job_id or not isinstance(lease_token, str):
            return {"status": "invalid_claim", "claimed": True}
        try:
            attempt_id = str(UUID(attempt_id))
        except (ValueError, TypeError, AttributeError):
            return {"status": "invalid_claim", "claimed": True, "job_id": job_id}

        task_id = job.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            task_id = "unknown"
        handler = job.get("handler")
        if not isinstance(handler, str) or not handler:
            handler = "unknown"
        system_actor = "system:worker:" + self.worker_id[:80]
        authenticated_actor: str | None = None
        self._audit_best_effort(job_id=job_id, task_id=task_id, attempt_id=attempt_id,
            action="job.claimed", actor=system_actor, handler=handler, outcome="claimed")
        try:
            if task_id == "unknown":
                raise WorkerError("task_missing")
            stored = self.queue.store.get_task(task_id)
            if not isinstance(stored, dict) or not isinstance(stored.get("task"), dict):
                raise WorkerError("task_missing")
            task = stored["task"]

            approval_required = task.get("approval_required")
            approval_status = task.get("approval_status")
            if not isinstance(approval_required, bool):
                raise HandlerPermissionError("approval_required invalide.")
            if approval_status is not None and (
                not isinstance(approval_status, str)
                or approval_status not in {"not_required", "pending", "approved", "rejected"}
            ):
                raise HandlerPermissionError("approval_status invalide.")
            if approval_required and approval_status != "approved":
                raise HandlerPermissionError("Approbation requise.")
            if not approval_required and approval_status not in (None, "not_required"):
                raise HandlerPermissionError("État d'approbation incohérent.")

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
            principal = authorization.get("principal")
            authenticated_actor = getattr(principal, "agent_id", None)
            if not isinstance(authenticated_actor, str) or authenticated_actor != agent_id:
                raise AccessDenied("Principal authentifié invalide.")
            authorize_job(job, task, self.policy, self.registry)

            if not self.queue.renew(job_id=job_id, worker_id=self.worker_id,
                                     lease_token=lease_token, lease_seconds=900):
                self._audit_best_effort(job_id=job_id, task_id=task_id, attempt_id=attempt_id,
                    action="job.lease_lost", actor=system_actor, handler=handler,
                    outcome="lease_lost_before_handler")
                return {"status": "lease_lost", "claimed": True, "job_id": job_id,
                        "attempt_id": attempt_id}

            try:
                self._audit(job_id=job_id, task_id=task_id, attempt_id=attempt_id,
                    action="job.handler_started", actor=authenticated_actor,
                    handler=handler, outcome="started")
            except Exception:
                return self._fail_job(job_id=job_id, task_id=task_id, attempt_id=attempt_id,
                    lease_token=lease_token, error_code="audit_unavailable", status="audit_blocked",
                    actor=authenticated_actor, action="job.failed", handler=handler,
                    outcome="audit_unavailable")

            def ensure_lease() -> None:
                if not self.queue.renew(job_id=job_id, worker_id=self.worker_id,
                                        lease_token=lease_token, lease_seconds=900):
                    raise LeaseLostError("lease_lost")

            result = execute_authorized_job(
                job, task, self.policy, self.registry,
                context={"worker_id": self.worker_id, "task_id": task_id,
                         "attempt_id": attempt_id, "authenticated_agent_id": authenticated_actor,
                         "authenticated_principal": principal, "ensure_lease": ensure_lease},
            )
            if not self.queue.complete(job_id=job_id, worker_id=self.worker_id,
                                        lease_token=lease_token, result=result):
                self._audit_best_effort(job_id=job_id, task_id=task_id, attempt_id=attempt_id,
                    action="job.lease_lost", actor=system_actor, handler=handler, outcome="lease_lost")
                return {"status": "lease_lost", "claimed": True, "job_id": job_id,
                        "attempt_id": attempt_id}
            self._audit_best_effort(job_id=job_id, task_id=task_id, attempt_id=attempt_id,
                action="job.completed", actor=authenticated_actor, handler=handler, outcome="completed")
            return {"status": "completed", "claimed": True, "job_id": job_id,
                    "attempt_id": attempt_id}
        except LeaseLostError:
            self._audit_best_effort(job_id=job_id, task_id=task_id, attempt_id=attempt_id,
                action="job.lease_lost", actor=system_actor, handler=handler, outcome="lease_lost_during_handler")
            return {"status": "lease_lost", "claimed": True, "job_id": job_id,
                    "attempt_id": attempt_id}
        except AuthenticatedAuthorizationDenied as exc:
            denied_actor = getattr(exc.principal, "agent_id", None)
            return self._fail_job(job_id=job_id, task_id=task_id, attempt_id=attempt_id,
                lease_token=lease_token, error_code="permission_denied", status="blocked",
                actor=denied_actor if isinstance(denied_actor, str) else system_actor,
                action="job.blocked", handler=handler, outcome="authenticated_agent_permission_denied")
        except AccessDenied:
            return self._fail_job(job_id=job_id, task_id=task_id, attempt_id=attempt_id,
                lease_token=lease_token, error_code="authentication_failed", status="blocked",
                actor=system_actor, action="job.authentication_blocked", handler=handler, outcome="blocked")
        except HandlerPermissionError:
            return self._fail_job(job_id=job_id, task_id=task_id, attempt_id=attempt_id,
                lease_token=lease_token, error_code="permission_denied", status="blocked",
                actor=authenticated_actor or system_actor, action="job.blocked",
                handler=handler, outcome="permission_denied")
        except (WorkerError, StoreError, QueueError):
            return self._fail_job(job_id=job_id, task_id=task_id, attempt_id=attempt_id,
                lease_token=lease_token, error_code="worker_validation_error", status="failed",
                actor=authenticated_actor or system_actor, action="job.failed",
                handler=handler, outcome="validation_error")
        except Exception:
            return self._fail_job(job_id=job_id, task_id=task_id, attempt_id=attempt_id,
                lease_token=lease_token, error_code="handler_error", status="failed",
                actor=authenticated_actor or system_actor, action="job.failed",
                handler=handler, outcome="handler_error")
