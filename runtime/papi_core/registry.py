"""Validation et routage déterministe des tâches PAPI.

Ce module ne contacte aucun service externe et n'exécute aucune action métier.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
AGENTS_FILE = ROOT / "data" / "agents.json"
TASKS_FILE = ROOT / "data" / "tasks.json"
VALID_STATUSES = {"backlog", "ready", "in_progress", "blocked", "review", "done", "cancelled"}
VALID_PRIORITIES = {"low", "normal", "high", "urgent"}
VALID_APPROVALS = {"not_required", "pending", "approved", "rejected"}


class RegistryError(ValueError):
    """Erreur de cohérence du registre."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"Impossible de lire {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RegistryError(f"{path} doit contenir un objet JSON.")
    return value


def load_agents(path: Path = AGENTS_FILE) -> dict[str, dict[str, Any]]:
    data = load_json(path)
    agents = data.get("agents")
    if not isinstance(agents, list) or not agents:
        raise RegistryError("Le registre doit contenir une liste non vide 'agents'.")
    result: dict[str, dict[str, Any]] = {}
    for agent in agents:
        if not isinstance(agent, dict) or not agent.get("id") or not agent.get("name"):
            raise RegistryError("Chaque agent doit avoir un id et un name.")
        if agent["id"] in result:
            raise RegistryError(f"Identifiant d'agent dupliqué: {agent['id']}")
        result[agent["id"]] = agent
    return result



def _normalized_agent_name(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(ch for ch in folded if not unicodedata.combining(ch)).split())


def validate_agent_directory(path: Path = AGENTS_FILE) -> dict[str, Any]:
    """Validate canonical agent identities and return a safe organization summary."""
    data = load_json(path)
    agents = data.get("agents")
    if not isinstance(agents, list) or not agents:
        raise RegistryError("Le registre doit contenir une liste non vide 'agents'.")

    errors: list[str] = []
    ids: set[str] = set()
    names: dict[str, list[str]] = {}
    departments: Counter[str] = Counter()
    allowed_statuses = {"defined", "planned", "active", "suspended", "revoked"}

    for index, agent in enumerate(agents):
        label = f"Agent #{index + 1}"
        if not isinstance(agent, dict):
            errors.append(f"{label}: objet attendu.")
            continue
        agent_id = agent.get("id")
        name = agent.get("name")
        role = agent.get("role")
        department = agent.get("department")
        status = agent.get("status")
        if not isinstance(agent_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,99}", agent_id):
            errors.append(f"{label}: identifiant invalide.")
        elif agent_id in ids:
            errors.append(f"Identifiant d'agent dupliqué: {agent_id}")
        else:
            ids.add(agent_id)
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{label}: nom affiché absent ou invalide.")
        else:
            names.setdefault(_normalized_agent_name(name), []).append(agent_id or label)
        if not isinstance(role, str) or not role.strip():
            errors.append(f"{label}: fonction absente ou invalide.")
        if not isinstance(department, str) or not department.strip():
            errors.append(f"{label}: département absent ou invalide.")
        else:
            departments[department.strip()] += 1
        if status not in allowed_statuses:
            errors.append(f"{label}: statut invalide.")
        for field in ("permissions", "prohibited"):
            values = agent.get(field)
            if not isinstance(values, list) or any(not isinstance(item, str) or not item.strip() for item in values):
                errors.append(f"{label}: {field} doit être une liste de chaînes non vides.")
            elif len(values) != len(set(values)):
                errors.append(f"{label}: valeur dupliquée dans {field}.")
        manager = agent.get("manager_agent_id")
        if manager is not None and (not isinstance(manager, str) or not manager.strip()):
            errors.append(f"{label}: manager_agent_id invalide.")

    for normalized, matching_ids in sorted(names.items()):
        if len(matching_ids) > 1:
            errors.append(
                "Nom affiché ambigu après normalisation : "
                + ", ".join(matching_ids)
                + f" (clé={normalized})."
            )

    for agent in agents:
        if isinstance(agent, dict):
            manager = agent.get("manager_agent_id")
            if manager and manager not in ids:
                errors.append(f"Responsable hiérarchique inconnu pour {agent.get('id', 'agent inconnu')}: {manager}")

    return {
        "valid": not errors,
        "agent_count": len(agents),
        "department_count": len(departments),
        "departments": dict(sorted(departments.items())),
        "status_counts": dict(sorted(Counter(
            item.get("status", "invalid") for item in agents if isinstance(item, dict)
        ).items())),
        "errors": errors,
    }


def validate_task(task: dict[str, Any], agents: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    required = ("id", "title", "department", "owner_agent", "status", "priority", "created_at", "approval_required")
    for field in required:
        if field not in task:
            errors.append(f"Champ obligatoire absent: {field}")
    if task.get("status") not in VALID_STATUSES:
        errors.append("Statut de tâche invalide.")
    if task.get("priority") not in VALID_PRIORITIES:
        errors.append("Priorité invalide.")
    if not isinstance(task.get("approval_required"), bool):
        errors.append("approval_required doit être booléen.")
    owner = task.get("owner_agent")
    if owner and owner not in agents:
        errors.append(f"Agent inconnu: {owner}")
    if task.get("approval_status") not in (None, *VALID_APPROVALS):
        errors.append("approval_status invalide.")
    if task.get("approval_required") and task.get("approval_status") != "approved" and task.get("status") in {"in_progress", "done"}:
        errors.append("Une tâche nécessitant une approbation ne peut démarrer/être terminée sans approbation.")
    if task.get("status") == "done" and not task.get("evidence") and not task.get("result_url"):
        errors.append("Une tâche terminée doit fournir une preuve ou un lien de résultat.")
    return errors


def validate_registries(agents_path: Path = AGENTS_FILE, tasks_path: Path = TASKS_FILE) -> list[str]:
    agents = load_agents(agents_path)
    data = load_json(tasks_path)
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        raise RegistryError("'tasks' doit être une liste.")
    errors: list[str] = []
    seen: set[str] = set()
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            errors.append(f"Tâche #{index + 1}: objet attendu.")
            continue
        task_id = task.get("id", f"#{index + 1}")
        if task_id in seen:
            errors.append(f"Identifiant de tâche dupliqué: {task_id}")
        seen.add(task_id)
        errors.extend(f"Tâche {task_id}: {error}" for error in validate_task(task, agents))
    return errors


def route_department(department: str, agents_path: Path = AGENTS_FILE) -> list[dict[str, str]]:
    """Retourne des candidats documentaires, jamais une affectation exécutée."""
    agents = load_agents(agents_path)
    return [
        {"id": agent["id"], "name": agent["name"], "role": agent.get("role", ""), "status": agent.get("status", "unknown")}
        for agent in agents.values()
        if agent.get("department", "").casefold() == department.casefold()
    ]
