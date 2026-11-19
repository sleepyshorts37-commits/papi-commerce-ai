"""Read-only audit of declared agent permissions and runtime blockers."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .authz import AccessDenied, authorize_agent, load_policy
from .registry import RegistryError, load_agents
from .security import validate_policy

ROOT = Path(__file__).resolve().parents[2]
AGENTS_FILE = ROOT / "data" / "agents.json"
POLICY_FILE = ROOT / "config" / "policy.json"
_PERMISSION_RE = re.compile(r"[a-z][a-z0-9_]{0,63}")


def _blocked_report(reason: str) -> dict[str, Any]:
    return {
        "mode": "read_only_local",
        "status": "blocked",
        "identity_authenticated": False,
        "handler_execution_verified": False,
        "runtime_execution_available": False,
        "errors": [reason],
        "summary": {
            "agents": 0,
            "permission_declarations": 0,
            "local_allow": 0,
            "local_deny": 0,
            "runtime_blocked": 0,
        },
        "agents": [],
    }


def _string_list(value: Any, field: str) -> tuple[list[str], list[str]]:
    if not isinstance(value, list):
        return [], [f"{field} doit être une liste."]
    errors: list[str] = []
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not _PERMISSION_RE.fullmatch(item):
            errors.append(f"{field}[{index}] doit être une permission ASCII minuscule valide.")
        else:
            result.append(item)
    if len(result) != len(set(result)):
        errors.append(f"{field} contient des doublons.")
    return result, errors


def build_agent_permission_report(
    agents_path: Path = AGENTS_FILE,
    policy_path: Path = POLICY_FILE,
) -> dict[str, Any]:
    """Audite les déclarations et les contrôles locaux sans authentifier/exécuter."""
    try:
        agents = load_agents(agents_path)
    except RegistryError:
        return _blocked_report("Registre agents absent ou invalide.")

    try:
        policy = load_policy(policy_path)
    except AccessDenied:
        return _blocked_report("Politique globale absente ou invalide.")

    policy_errors = validate_policy(policy)
    execution_enabled = policy.get("execution_enabled") is True
    external_actions_enabled = policy.get("external_actions_enabled") is True
    errors = list(policy_errors)
    agent_reports: list[dict[str, Any]] = []
    local_allow = 0
    local_deny = 0
    declarations = 0
    runtime_blocked = 0

    for agent_id, agent in agents.items():
        agent_errors: list[str] = []
        if not isinstance(agent_id, str) or not agent_id.strip():
            agent_errors.append("Identifiant d'agent invalide.")
        if not isinstance(agent.get("name"), str) or not agent["name"].strip():
            agent_errors.append("Nom d'agent invalide.")
        status = agent.get("status")
        if not isinstance(status, str) or not status.strip():
            agent_errors.append("Statut d'agent invalide.")

        permissions, permission_errors = _string_list(agent.get("permissions"), "permissions")
        prohibited, prohibited_errors = _string_list(agent.get("prohibited"), "prohibited")
        agent_errors.extend(permission_errors)
        agent_errors.extend(prohibited_errors)
        overlap = sorted(set(permissions).intersection(prohibited))
        if overlap:
            agent_errors.append("Permissions également interdites : " + ", ".join(overlap) + ".")

        permission_reports: list[dict[str, Any]] = []
        for permission in permissions:
            declarations += 1
            is_prohibited = permission in prohibited
            local_blockers: list[str] = []
            if policy_errors:
                local_blockers.append("global_policy_invalid")
            if agent_errors:
                local_blockers.append("agent_registry_invalid")
            if is_prohibited:
                local_blockers.append("explicit_agent_prohibition")

            local_check = "deny"
            reason = "Déclaration ou politique invalide : refus par défaut."
            if not local_blockers:
                try:
                    authorize_agent(agent_id, permission, agents_path, policy)
                    local_check = "allow"
                    reason = "Permission déclarée et autorisée par le contrôle local."
                except AccessDenied as exc:
                    reason = str(exc)
                    local_blockers.append("local_authorization_denied")

            runtime_blockers = list(local_blockers)
            if status != "active":
                runtime_blockers.append("agent_not_active")
            if not execution_enabled:
                runtime_blockers.append("execution_disabled")
            runtime_blockers.append("runtime_identity_task_handler_not_verified")

            if local_check == "allow":
                local_allow += 1
            else:
                local_deny += 1
            runtime_blocked += 1

            permission_reports.append({
                "permission": permission,
                "declared": True,
                "explicitly_prohibited": is_prohibited,
                "local_check": local_check,
                "reason": reason,
                "runtime_gate": "blocked",
                "runtime_blockers": runtime_blockers,
            })

        agent_reports.append({
            "id": agent_id if isinstance(agent_id, str) else "invalid_id",
            "name": agent.get("name") if isinstance(agent.get("name"), str) else "invalid_name",
            "status": status if isinstance(status, str) else "invalid_status",
            "permissions_declared": len(permissions),
            "prohibited_declared": len(prohibited),
            "errors": agent_errors,
            "permissions": permission_reports,
        })
        errors.extend(f"Agent {agent_id}: {error}" for error in agent_errors)

    return {
        "mode": "read_only_local",
        "status": "blocked" if errors else "ok",
        "identity_authenticated": False,
        "handler_execution_verified": False,
        "runtime_execution_available": False,
        "execution_enabled": execution_enabled,
        "external_actions_enabled": external_actions_enabled,
        "policy_validation_errors": policy_errors,
        "errors": errors,
        "summary": {
            "agents": len(agent_reports),
            "permission_declarations": declarations,
            "local_allow": local_allow,
            "local_deny": local_deny,
            "runtime_blocked": runtime_blocked,
        },
        "agents": agent_reports,
    }
