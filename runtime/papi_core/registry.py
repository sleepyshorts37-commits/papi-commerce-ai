"""Validation et routage déterministe des tâches PAPI.

Ce module ne contacte aucun service externe et n'exécute aucune action métier.
"""
from __future__ import annotations

import json
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
