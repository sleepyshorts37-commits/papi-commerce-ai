"""Registre fermé de handlers et autorisation avant toute exécution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


class PermissionError(RuntimeError):
    """Handler inconnu ou action non autorisée."""


ACTION_CLASSES = {
    "read_only",
    "internal_write",
    "external_communication",
    "financial",
    "legal",
}


@dataclass(frozen=True)
class HandlerSpec:
    name: str
    action_class: str
    function: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


class HandlerRegistry:
    """Registre explicite : aucun import ou code dynamique depuis un job."""

    def __init__(self) -> None:
        self._handlers: dict[str, HandlerSpec] = {}

    def register(self, name: str, action_class: str, function: Callable) -> None:
        if not isinstance(name, str) or not name.strip() or len(name) > 100:
            raise PermissionError("Nom de handler invalide.")
        if name in self._handlers:
            raise PermissionError("Ce handler est déjà enregistré.")
        if action_class not in ACTION_CLASSES:
            raise PermissionError("Classe d'action inconnue.")
        if not callable(function):
            raise PermissionError("Le handler doit être appelable.")
        self._handlers[name] = HandlerSpec(name, action_class, function)

    def get(self, name: str) -> HandlerSpec:
        try:
            return self._handlers[name]
        except (KeyError, TypeError) as exc:
            raise PermissionError("Handler absent du registre autorisé.") from exc


def authorize_job(
    job: dict[str, Any],
    task: dict[str, Any],
    policy: dict[str, Any],
    registry: HandlerRegistry,
) -> HandlerSpec:
    """Vérifie toutes les barrières ; ne lance jamais le handler."""
    if not isinstance(job, dict) or not isinstance(task, dict) or not isinstance(policy, dict):
        raise PermissionError("Job, tâche et politique doivent être des objets.")
    name = job.get("handler")
    spec = registry.get(name)
    allowed = policy.get("allowed_handlers", [])
    if not isinstance(allowed, list) or name not in allowed:
        raise PermissionError("Handler non autorisé par la politique.")
    if policy.get("execution_enabled") is not True:
        raise PermissionError("Exécution désactivée par défaut.")
    if task.get("status") != "in_progress":
        raise PermissionError("La tâche doit être au statut in_progress.")
    approval_required = task.get("approval_required")
    approval_status = task.get("approval_status")
    if not isinstance(approval_required, bool):
        raise PermissionError("Indicateur approval_required invalide : accès fermé.")
    if approval_status is not None and (
        not isinstance(approval_status, str)
        or approval_status not in {"not_required", "pending", "approved", "rejected"}
    ):
        raise PermissionError("Statut d'approbation invalide : accès fermé.")
    if approval_required and approval_status != "approved":
        raise PermissionError("Approbation du propriétaire requise.")
    if not approval_required and approval_status not in (None, "not_required"):
        raise PermissionError("État d'approbation incohérent : accès fermé.")
    permissions = policy.get("action_permissions", {})
    rule = permissions.get(spec.action_class, {}) if isinstance(permissions, dict) else {}
    if not isinstance(rule, dict) or rule.get("enabled") is not True:
        raise PermissionError("Cette catégorie d'action est désactivée.")
    if rule.get("owner_approval") is True and task.get("approval_status") != "approved":
        raise PermissionError("Approbation explicite requise pour cette catégorie.")
    if spec.action_class in {"external_communication", "financial", "legal"}:
        if policy.get("external_actions_enabled") is not True:
            raise PermissionError("Les actions externes sont désactivées.")
    return spec


def execute_authorized_job(
    job: dict[str, Any],
    task: dict[str, Any],
    policy: dict[str, Any],
    registry: HandlerRegistry,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Exécute uniquement un handler enregistré et autorisé ; renvoie un résultat borné."""
    spec = authorize_job(job, task, policy, registry)
    payload = job.get("payload", {})
    if not isinstance(payload, dict):
        raise PermissionError("Payload invalide.")
    result = spec.function(payload, context or {})
    if not isinstance(result, dict):
        raise PermissionError("Le handler doit retourner un objet résultat.")
    return {"handler": spec.name, "status": "completed", "result": result}
