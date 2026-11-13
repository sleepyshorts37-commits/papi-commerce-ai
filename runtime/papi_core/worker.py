"""Worker à un seul job ; authentification et journal d'audit avant handler."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .audit import append_event, new_event
from .authz import AccessDenied, authorize_authenticated_agent, authorize_service_agent
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
                 service_id: str | None = None,
                 service_audience: str | None = None,
                 audit_path: Path | None = None) -> None:
        if not isinstance(worker_id, str) or not worker_id.strip():
            raise WorkerError("Identifiant worker obligatoire.")
        if not isinstance(policy, dict):
            raise WorkerError("Politique invalide.")
        require_service_audience = policy.get("require_service_audience", False)
        if not isinstance(require_service_audience, bool):
            raise WorkerError("Politique require_service_audience invalide.")
        configured_service = isinstance(service_id, str) and bool(service_id.strip())
        configured_audience = isinstance(service_audience, str) and bool(service_audience.strip())
        if configured_service != configured_audience:
            raise WorkerError("service_id et service_audience doivent être configurés ensemble.")
        if require_service_audience and not (configured_service and configured_audience):
            raise WorkerError("Identité et audience du service obligatoires.")
        if not require_service_audience and (configured_service or configured_audience):
            raise WorkerError("La configuration de service exige require_service_audience=true.")
        self.service_id = service_id.strip() if configured_service else None
        self.service_audience = service_audience.strip() if configured_audience else None
        self.require_service_audience = require_service_audience
        self.queue, self.registry, self.policy, self.worker_id = queue, registry, policy, worker_id
        self.key_dir, self.replay_db, self.public_registry = key_dir, replay_db, public_registry
        self.shared_identity_verifier = shared_identity_verifier
        self.audit_path = Path(audit_path) if audit_path is not None else Path.home() / ".papi" / "audit" / "events.jsonl"

    def _audit(self, job_id: str, action: str, actor: str, *, handler: str = "unknown",
               outcome: str = "ok") -> bool:
        """Écrit des métadonnées bornées ; aucun payload, secret, exception ou lease."""
        job_digest = hashlib.sha256(job_id.encode("utf-8")).hexdigest()
        event_digest = hashlib.sha256((job_digest + ":" + action).encode("utf-8")).hexdigest()
        event = new_event(
            event_id="worker:" + event_digest,
            actor=actor,
            action=action,
            entity_type="job",
            entity_id=job_digest,
            details={"worker_id": self.worker_id[:100], "handler": handler[:120],
                     "outcome": outcome[:80]},
        )
        append_event(event, self.audit_path)
        return True

    def _audit_best_effort(self, *args: Any, **kwargs: Any) -> None:
        try:
            self._audit(*args, **kwargs)
        except Exception:
            # Une transition durable de queue ne peut pas être annulée par l'audit terminal.
            return

    def _fail_job(self, *, job_id: str, lease_token: str, error_code: str,
                  status: str, actor: str, action: str, handler: str,
                  outcome: str, attempt: int = 1,
                  max_attempts: int = 5) -> dict[str, Any]:
        """Convertit aussi un échec de transition queue en résultat contrôlé."""
        try:
            self.queue.fail(job_id=job_id, worker_id=self.worker_id,
                            lease_token=lease_token, error_code=error_code,
                            attempt=attempt, max_attempts=max_attempts)
        except Exception:
            self._audit_best_effort(job_id, "job.failure_transition_error", actor,
                                    handler=handler, outcome="queue_fail_error")
            return {"status": "failure_transition_error", "claimed": True, "job_id": job_id}
        self._audit_best_effort(job_id, action, actor, handler=handler, outcome=outcome)
        return {"status": status, "claimed": True, "job_id": job_id}

    def run_once(self) -> dict[str, Any]:
        """Traite au maximum un travail ; l'audit handler_started est fail-closed."""
        if self.policy.get("execution_enabled") is not True:
            return {"status": "disabled", "claimed": False}
        job = self.queue.claim(worker_id=self.worker_id)
        if job is None:
            return {"status": "idle", "claimed": False}
        job_id, lease_token = job.get("id"), job.get("lease_token")
        if not isinstance(job_id, str) or not job_id or not isinstance(lease_token, str):
            return {"status": "invalid_claim", "claimed": True}

        system_actor = "system:worker:" + self.worker_id[:80]
        self._audit_best_effort(job_id, "job.claimed", system_actor)
        handler = job.get("handler")
        if not isinstance(handler, str) or not handler:
            handler = "unknown"
        authenticated_actor: str | None = None
        try:
            task_id = job.get("task_id")
            if not isinstance(task_id, str) or not task_id:
                raise WorkerError("task_missing")
            stored = self.queue.store.get_task(task_id)
            if not isinstance(stored, dict) or not isinstance(stored.get("task"), dict):
                raise WorkerError("task_missing")
            task = stored["task"]

            # Fail closed avant l'authentification : ce contrôle local reste
            # effectif même si le durcissement global de authorize_job n'est
            # pas encore intégré à main.
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

            # Le handler est résolu avant authentification ; les refus de politique
            # seront évalués après authentification pour attribuer correctement l'audit.
            spec = self.registry.get(handler)
            permission = PERMISSION_BY_CLASS.get(spec.action_class)
            if permission is None:
                raise AccessDenied("Classe de permission non prise en charge.")
            agent_id = task.get("owner_agent")
            if self.require_service_audience:
                authorization = authorize_service_agent(
                    agent_id, permission, job.get("agent_identity"),
                    task_id=task_id, handler=handler,
                    audience=self.service_audience, service_id=self.service_id,
                    policy=self.policy, key_dir=self.key_dir,
                    replay_db=self.replay_db, public_registry=self.public_registry,
                    shared_identity_verifier=self.shared_identity_verifier,
                )
            else:
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
            # Fencing: ne jamais démarrer le handler avec un bail expiré ou perdu.
            if not self.queue.renew(job_id=job_id, worker_id=self.worker_id,
                                    lease_token=lease_token, lease_seconds=900):
                self._audit_best_effort(job_id, "job.lease_lost", system_actor,
                                        handler=handler, outcome="lease_lost_before_handler")
                return {"status": "lease_lost", "claimed": True, "job_id": job_id}

            try:
                self._audit(job_id, "job.handler_started", authenticated_actor, handler=handler)
            except Exception:
                return self._fail_job(job_id=job_id, lease_token=lease_token,
                                      attempt=job.get("attempts", 1),
                                      max_attempts=job.get("max_attempts", 5),
                                      error_code="audit_unavailable", status="audit_blocked",
                                      actor=authenticated_actor, action="job.failed",
                                      handler=handler, outcome="audit_unavailable")

            def ensure_lease() -> None:
                """Renouvelle le bail ; à appeler avant chaque effet externe et périodiquement."""
                if not self.queue.renew(job_id=job_id, worker_id=self.worker_id,
                                        lease_token=lease_token, lease_seconds=900):
                    raise LeaseLostError("lease_lost")

            result = execute_authorized_job(
                job, task, self.policy, self.registry,
                context={"worker_id": self.worker_id, "task_id": task_id,
                         "authenticated_agent_id": authenticated_actor,
                         "authenticated_principal": principal,
                         "ensure_lease": ensure_lease},
            )
            if not self.queue.complete(job_id=job_id, worker_id=self.worker_id,
                                        lease_token=lease_token, result=result):
                self._audit_best_effort(job_id, "job.lease_lost", system_actor, handler=handler,
                                        outcome="lease_lost")
                return {"status": "lease_lost", "claimed": True, "job_id": job_id}
            self._audit_best_effort(job_id, "job.completed", authenticated_actor, handler=handler)
            return {"status": "completed", "claimed": True, "job_id": job_id}
        except LeaseLostError:
            self._audit_best_effort(job_id, "job.lease_lost", system_actor,
                                    handler=handler, outcome="lease_lost_during_handler")
            return {"status": "lease_lost", "claimed": True, "job_id": job_id}
        except AccessDenied:
            return self._fail_job(job_id=job_id, lease_token=lease_token,
                                  error_code="authentication_failed", status="blocked",
                                  actor=system_actor, action="job.authentication_blocked",
                                  handler=handler, outcome="blocked")
        except HandlerPermissionError:
            return self._fail_job(job_id=job_id, lease_token=lease_token,
                                  error_code="permission_denied", status="blocked",
                                  actor=authenticated_actor or system_actor, action="job.blocked",
                                  handler=handler, outcome="permission_denied")
        except (WorkerError, StoreError, QueueError):
            return self._fail_job(job_id=job_id, lease_token=lease_token,
                                  error_code="worker_validation_error", status="failed",
                                  actor=authenticated_actor or system_actor, action="job.failed",
                                  handler=handler, outcome="validation_error")
        except Exception:
            return self._fail_job(job_id=job_id, lease_token=lease_token,
                                  error_code="handler_error", status="failed",
                                  actor=authenticated_actor or system_actor, action="job.failed",
                                  handler=handler, outcome="handler_error")
