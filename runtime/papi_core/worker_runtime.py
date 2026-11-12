"""Moteur de dispatch PAPI à exécution strictement contrôlée."""
from __future__ import annotations

from typing import Any, Callable

from .execution_gate import evaluate_execution_readiness

Handler = Callable[[dict[str, Any]], dict[str, Any]]


class WorkerRuntimeError(RuntimeError):
    """Erreur contrôlée du moteur worker."""


def _echo(payload: dict[str, Any]) -> dict[str, Any]:
    return {"echo": payload}


def _preview(payload: dict[str, Any]) -> dict[str, Any]:
    title = payload.get("title")
    content = payload.get("content")
    if not isinstance(title, str) or not isinstance(content, str):
        raise WorkerRuntimeError("report.preview exige title et content textuels.")
    return {"title": title[:160], "preview": content[:2000], "preview_only": True}


BUILTIN_HANDLERS: dict[str, Handler] = {
    "internal.echo": _echo,
    "report.preview": _preview,
}


def run_worker_job(
    *,
    job: dict[str, Any],
    task: dict[str, Any],
    agent: dict[str, Any],
    identity: dict[str, Any],
    policy: dict[str, Any],
    auth_envelope: dict[str, Any],
    authenticate: Callable[[dict[str, Any]], dict[str, Any]],
    handlers: dict[str, Handler] | None = None,
) -> dict[str, Any]:
    """Authentifie un worker, valide la tâche, puis appelle un handler autorisé.

    Le callback authenticate doit effectuer la vérification Ed25519 complète
    (worker_auth.authenticate_worker_operation avec les chemins de registres).
    Un simple worker_id ou un booléen fourni par le job n'est jamais une preuve.
    """
    if not all(isinstance(value, dict) for value in
               (job, task, agent, identity, policy, auth_envelope)):
        raise WorkerRuntimeError("Les entrées du runtime doivent être des objets.")
    if not callable(authenticate):
        raise WorkerRuntimeError("Vérificateur worker obligatoire.")
    if job.get("id") != task.get("id") and job.get("task_id") != task.get("id"):
        raise WorkerRuntimeError("Le job ne correspond pas à la tâche.")
    if job.get("handler") != task.get("execution", {}).get("handler"):
        raise WorkerRuntimeError("Le handler du job diverge de la spécification de tâche.")

    try:
        auth = authenticate(auth_envelope)
    except Exception as exc:
        raise WorkerRuntimeError("Authentification worker refusée.") from exc
    if (not isinstance(auth, dict) or auth.get("worker_authenticated") is not True
        or auth.get("operation") not in {"heartbeat", "claim"}
        or auth.get("worker_id") != agent.get("id")):
        raise WorkerRuntimeError("Preuve worker insuffisante ou identité divergente.")
    if auth.get("operation") == "heartbeat" and auth.get("job_id") != job.get("id"):
        raise WorkerRuntimeError("La preuve heartbeat ne vise pas ce job.")
    if auth.get("operation") == "claim" and job.get("status") not in {"queued", "retry"}:
        raise WorkerRuntimeError("Un claim ne peut traiter que la file en attente.")

    readiness = evaluate_execution_readiness(task, agent, identity, policy)
    if readiness["eligible"] is not True:
        return {
            "job_id": job.get("id"), "status": "held",
            "reason": "execution_preflight_blocked",
            "reason_codes": readiness["reason_codes"],
            "handler_invoked": False,
        }

    registry = BUILTIN_HANDLERS if handlers is None else handlers
    handler_name = task["execution"]["handler"]
    handler = registry.get(handler_name)
    if not callable(handler) or handler_name not in policy.get("allowed_handlers", []):
        return {"job_id": job.get("id"), "status": "blocked",
                "reason": "handler_not_registered_or_allowed", "handler_invoked": False}
    payload = job.get("payload", {})
    if not isinstance(payload, dict):
        raise WorkerRuntimeError("Payload job invalide.")
    try:
        output = handler(payload)
    except Exception as exc:
        return {"job_id": job.get("id"), "status": "failed",
                "reason": "handler_error", "error_type": type(exc).__name__,
                "handler_invoked": True}
    if not isinstance(output, dict):
        raise WorkerRuntimeError("Un handler doit retourner un objet JSON.")
    return {"job_id": job.get("id"), "status": "completed",
            "result": output, "handler_invoked": True,
            "mode": "controlled_local_execution"}
