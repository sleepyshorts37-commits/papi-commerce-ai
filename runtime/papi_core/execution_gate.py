"""Prévalidation fail-closed d'une éventuelle tâche agent.

Ce module ne lance aucun handler, processus, appel réseau ou écriture.
Il produit uniquement une décision de prévalidation explicable.
"""
from __future__ import annotations

from typing import Any

from .agent_identity import validate_identity


class ExecutionGateError(ValueError):
    """Entrées de prévalidation mal formées."""


ACTION_CATEGORIES = {"read_only", "internal_write", "external_communication", "financial", "legal"}


def evaluate_execution_readiness(
    task: dict[str, Any],
    agent: dict[str, Any],
    identity: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    """Évalue si une tâche pourrait franchir les contrôles préalables.

    Même si 'eligible' vaut True, aucun travail n'est exécuté : ce résultat
    reste un rapport de prévalidation et ne constitue pas un jeton d'exécution.
    """
    if not all(isinstance(value, dict) for value in (task, agent, identity, policy)):
        raise ExecutionGateError("Tâche, agent, identité et politique doivent être des objets.")

    reasons: list[dict[str, str]] = []

    def block(code: str, detail: str) -> None:
        reasons.append({"code": code, "detail": detail})

    if policy.get("execution_enabled") is not True:
        block("EXECUTION_DISABLED", "L'exécution globale n'est pas explicitement activée.")

    if task.get("status") != "ready":
        block("TASK_NOT_READY", "La tâche doit être au statut ready.")
    if not isinstance(task.get("id"), str) or not task["id"].strip():
        block("TASK_ID_MISSING", "Identifiant de tâche absent.")
    if task.get("owner_agent") != agent.get("id"):
        block("TASK_OWNER_MISMATCH", "L'agent évalué n'est pas le propriétaire de la tâche.")

    if agent.get("status") != "active":
        block("AGENT_INACTIVE", "L'agent n'est pas actif dans le registre.")
    if identity.get("agent_id") != agent.get("id"):
        block("IDENTITY_AGENT_MISMATCH", "La carte d'identité ne correspond pas à l'agent.")
    if identity.get("status") != "active" or identity.get("profile_state") != "complete":
        block("IDENTITY_INCOMPLETE", "La carte doit être active et complète.")
    identity_errors = validate_identity(identity, {agent.get("id"): agent})
    if identity_errors:
        block("IDENTITY_INVALID", "La carte d'identité ne passe pas la validation structurelle.")
    if identity.get("permissions") != agent.get("permissions"):
        block("PERMISSION_DRIFT", "Les permissions de la carte et du registre divergent.")
    if identity.get("prohibited_actions") != agent.get("prohibited"):
        block("PROHIBITION_DRIFT", "Les interdictions de la carte et du registre divergent.")

    if task.get("approval_required") is True and task.get("approval_status") != "approved":
        block("OWNER_APPROVAL_REQUIRED", "L'approbation requise n'est pas enregistrée.")
    elif task.get("approval_required") not in (True, False):
        block("APPROVAL_FLAG_INVALID", "Le champ approval_required doit être booléen.")

    action = task.get("execution")
    if not isinstance(action, dict):
        action = {}
        block("EXECUTION_SPEC_MISSING", "La tâche ne contient pas de spécification execution.")
    handler = action.get("handler")
    permission = action.get("permission")
    category = action.get("category")
    if not isinstance(handler, str) or not handler.strip():
        block("HANDLER_MISSING", "Handler déclaré absent.")
    allowed_handlers = policy.get("allowed_handlers")
    if not isinstance(allowed_handlers, list) or handler not in allowed_handlers:
        block("HANDLER_NOT_ALLOWED", "Handler absent de la liste globale autorisée.")
    if not isinstance(permission, str) or not permission.strip():
        block("PERMISSION_MISSING", "Permission d'action absente.")
    else:
        if permission not in agent.get("permissions", []):
            block("PERMISSION_NOT_GRANTED", "L'agent ne possède pas la permission demandée.")
        if permission in agent.get("prohibited", []):
            block("ACTION_PROHIBITED", "L'action est interdite pour cet agent.")
        if permission in policy.get("never_allowed", []):
            block("GLOBALLY_PROHIBITED", "L'action est interdite par la politique globale.")
        if permission in policy.get("requires_owner_approval", []) and task.get("approval_status") != "approved":
            block("ACTION_APPROVAL_REQUIRED", "Cette permission exige une approbation propriétaire.")

    if category not in ACTION_CATEGORIES:
        block("ACTION_CATEGORY_INVALID", "Catégorie d'action absente ou non reconnue.")
    else:
        action_permissions = policy.get("action_permissions")
        category_policy = action_permissions.get(category, {}) if isinstance(action_permissions, dict) else {}
        if not isinstance(category_policy, dict) or category_policy.get("enabled") is not True:
            block("ACTION_CATEGORY_DISABLED", "Cette catégorie d'action est désactivée.")
        if category in {"external_communication", "financial", "legal"} and policy.get("external_actions_enabled") is not True and category == "external_communication":
            block("EXTERNAL_ACTIONS_DISABLED", "Les communications externes sont désactivées.")
        if category in {"financial", "legal"}:
            block("SENSITIVE_ACTION_REQUIRES_OWNER_REVIEW", "Les actions financières et juridiques restent bloquées dans ce précontrôle.")

    cost = action.get("cost_xof", 0)
    budget = policy.get("default_budget_xof", 0)
    if isinstance(cost, bool) or not isinstance(cost, int) or cost < 0:
        block("COST_INVALID", "Le coût doit être un entier positif ou nul en FCFA.")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 0:
        block("BUDGET_INVALID", "Le budget global doit être un entier positif ou nul en FCFA.")
    elif isinstance(cost, int) and not isinstance(cost, bool) and cost > budget:
        block("BUDGET_EXCEEDED", "Le coût dépasse le budget autorisé.")

    return {
        "task_id": task.get("id"),
        "agent_id": agent.get("id"),
        "eligible": not reasons,
        "decision": "preflight_passed" if not reasons else "blocked",
        "reason_codes": reasons,
        "execution_performed": False,
        "execution_token_issued": False,
        "mode": "preflight_only",
    }
