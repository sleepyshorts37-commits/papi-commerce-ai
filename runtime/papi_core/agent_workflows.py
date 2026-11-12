"""Planification déterministe de workflows multi-agents, sans exécution."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from .audit import validate_event
from .identity_security import validate_identity_registry

WORKFLOW_PERMISSION = "create_agent_workflows"
ACTIVE = {"active", "deployed"}
PRIORITIES = {"low", "normal", "high", "urgent"}
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,119}$")
_EMAIL = re.compile(r"\\b[^\\s@]+@[^\\s@]+\\.[^\\s@]+\\b")
_PHONE = re.compile(r"(?<!\\w)(?:\\+?\\d[\\d .()/-]{7,}\\d)(?!\\w)")


class AgentWorkflowError(ValueError):
    """Workflow invalide ou non autorisé."""


def _text(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise AgentWorkflowError(f"{field} doit contenir entre 1 et {maximum} caractères.")
    if _EMAIL.search(value) or _PHONE.search(value):
        raise AgentWorkflowError(f"{field} semble contenir une coordonnée personnelle.")
    return value.strip()


def _iso(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AgentWorkflowError(f"{field} doit être une date ISO-8601 avec fuseau.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AgentWorkflowError(f"{field} doit être une date ISO-8601 avec fuseau.") from exc
    if parsed.tzinfo is None:
        raise AgentWorkflowError(f"{field} doit inclure un fuseau horaire.")
    return value


def _topological_order(steps: list[dict[str, Any]]) -> list[str]:
    by_id = {step["step_id"]: step for step in steps}
    if len(by_id) != len(steps):
        raise AgentWorkflowError("Identifiant d'étape dupliqué.")
    indegree = {key: 0 for key in by_id}
    children = {key: [] for key in by_id}
    for step in steps:
        sid = step["step_id"]
        deps = step["depends_on"]
        if not isinstance(deps, list) or any(not isinstance(dep, str) for dep in deps):
            raise AgentWorkflowError("depends_on doit être une liste d'identifiants.")
        if len(deps) != len(set(deps)) or sid in deps:
            raise AgentWorkflowError("Dépendance dupliquée ou dépendance sur soi-même.")
        for dep in deps:
            if dep not in by_id:
                raise AgentWorkflowError(f"Dépendance inconnue : {dep}.")
            indegree[sid] += 1
            children[dep].append(sid)
    ready = sorted(key for key, count in indegree.items() if count == 0)
    order = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for child in sorted(children[current]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort()
    if len(order) != len(steps):
        raise AgentWorkflowError("Cycle détecté dans les dépendances du workflow.")
    return order


def build_workflow_candidate(
    *, workflow_id: str, name: str, description: str, creator_id: str,
    priority: str, created_at: str, steps: list[dict[str, Any]],
    identity_document: dict[str, Any], agents: dict[str, dict[str, Any]],
    due_at: str | None = None, approval_required: bool = True,
) -> dict[str, Any]:
    """Valide et prépare un plan de workflow ; aucune étape n'est affectée."""
    validate_identity_registry(identity_document)
    identities = {item["agent_id"]: item for item in identity_document["identities"]}
    creator, creator_registry = identities.get(creator_id), agents.get(creator_id)
    if not creator or not creator_registry:
        raise AgentWorkflowError("Créateur absent des registres.")
    if creator.get("status") not in ACTIVE or creator_registry.get("status") not in ACTIVE:
        raise AgentWorkflowError("Créateur non actif.")
    if creator.get("profile_state") != "complete":
        raise AgentWorkflowError("Profil du créateur incomplet.")
    if WORKFLOW_PERMISSION in creator.get("prohibited_actions", []) or WORKFLOW_PERMISSION not in creator.get("permissions", []):
        raise AgentWorkflowError("Permission create_agent_workflows absente ou interdite.")
    if not isinstance(workflow_id, str) or not _ID.fullmatch(workflow_id):
        raise AgentWorkflowError("workflow_id invalide.")
    if priority not in PRIORITIES or not isinstance(approval_required, bool):
        raise AgentWorkflowError("Priorité ou approval_required invalide.")
    clean_name = _text(name, "name", 160)
    clean_description = _text(description, "description", 500)
    _iso(created_at, "created_at")
    if due_at is not None:
        _iso(due_at, "due_at")
    if not isinstance(steps, list) or not steps or len(steps) > 50:
        raise AgentWorkflowError("Le workflow doit contenir entre 1 et 50 étapes.")
    normalized = []
    required = {"step_id", "title", "instructions", "assignee_id", "depends_on", "acceptance_criteria", "reviewer_id", "approval_required"}
    for raw in steps:
        if not isinstance(raw, dict) or set(raw) != required:
            raise AgentWorkflowError("Schéma d'étape invalide.")
        sid = raw["step_id"]
        if not isinstance(sid, str) or not _ID.fullmatch(sid):
            raise AgentWorkflowError("step_id invalide.")
        assignee_id, reviewer_id = raw["assignee_id"], raw["reviewer_id"]
        for agent_id, label in ((assignee_id, "destinataire"), (reviewer_id, "réviseur")):
            identity, registry = identities.get(agent_id), agents.get(agent_id)
            if not identity or not registry:
                raise AgentWorkflowError(f"Agent {label} absent des registres.")
            if identity.get("status") not in ACTIVE or registry.get("status") not in ACTIVE:
                raise AgentWorkflowError(f"Agent {label} non actif.")
            if identity.get("profile_state") != "complete":
                raise AgentWorkflowError(f"Profil de l'agent {label} incomplet.")
        if reviewer_id == assignee_id:
            raise AgentWorkflowError("Le réviseur doit être distinct de l'exécutant.")
        criteria = raw["acceptance_criteria"]
        if not isinstance(criteria, list) or not criteria or len(criteria) > 10:
            raise AgentWorkflowError("Chaque étape exige de 1 à 10 critères d'acceptation.")
        clean_criteria = [_text(v, "acceptance_criteria", 200) for v in criteria]
        if not isinstance(raw["approval_required"], bool):
            raise AgentWorkflowError("approval_required d'étape doit être booléen.")
        normalized.append({
            "step_id": sid, "title": _text(raw["title"], "step title", 160),
            "instructions": _text(raw["instructions"], "step instructions", 500),
            "assignee_id": assignee_id, "depends_on": list(raw["depends_on"]),
            "acceptance_criteria": clean_criteria, "reviewer_id": reviewer_id,
            "approval_required": raw["approval_required"],
            "quality_gate": {"required": True, "reviewer_id": reviewer_id,
                             "evidence_required": True, "pass_without_evidence": False},
            "status": "planned_not_assigned",
        })
    order = _topological_order(normalized)
    details = {
        "workflow_id": workflow_id, "name": clean_name,
        "description": clean_description, "creator_id": creator_id,
        "priority": priority, "due_at": due_at,
        "approval_required": approval_required, "steps": normalized,
        "topological_order": order,
    }
    event = {
        "event_id": f"WORKFLOW-EVENT-{workflow_id}", "occurred_at": created_at,
        "actor": creator_id, "action": "agent.workflow.proposed",
        "entity_type": "agent_workflow", "entity_id": workflow_id,
        "details": details,
    }
    try:
        validate_event(event)
    except ValueError as exc:
        raise AgentWorkflowError(str(exc)) from exc
    return {
        "status": "proposal_candidate", "workflow": details,
        "permission_checked": WORKFLOW_PERMISSION,
        "runtime_identity_authenticated": False, "owner_approval_checked": False,
        "tasks_created": 0, "agents_notified": 0, "workers_started": 0,
        "workflow_persisted": False, "read_only": True,
    }


def build_workflow_center(events: list[dict[str, Any]], identity_document: dict[str, Any],
                          agents: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Projette uniquement les propositions explicitement présentes dans l'audit."""
    validate_identity_registry(identity_document)
    identities = {item["agent_id"]: item for item in identity_document["identities"]}
    seen, workflows, rejected = set(), [], 0
    for event in events:
        if not isinstance(event, dict) or event.get("action") != "agent.workflow.proposed":
            continue
        try:
            validate_event(event)
            if event["entity_type"] != "agent_workflow":
                raise AgentWorkflowError("Type d'entité invalide.")
            d = event["details"]
            workflow_id, creator_id = d["workflow_id"], event["actor"]
            if workflow_id in seen or event["entity_id"] != workflow_id:
                raise AgentWorkflowError("Identifiant de workflow dupliqué ou incohérent.")
            creator = identities.get(creator_id)
            if not creator or creator.get("status") not in ACTIVE or creator.get("profile_state") != "complete":
                raise AgentWorkflowError("Créateur inconnu, inactif ou incomplet.")
            if WORKFLOW_PERMISSION not in creator.get("permissions", []) or WORKFLOW_PERMISSION in creator.get("prohibited_actions", []):
                raise AgentWorkflowError("Permission de création absente ou interdite.")
            _topological_order(d["steps"])
            for step in d["steps"]:
                for agent_id in (step["assignee_id"], step["reviewer_id"]):
                    identity, registry = identities.get(agent_id), agents.get(agent_id)
                    if not identity or not registry or identity.get("status") not in ACTIVE or registry.get("status") not in ACTIVE or identity.get("profile_state") != "complete":
                        raise AgentWorkflowError("Agent d'étape inconnu, inactif ou incomplet.")
                if step["assignee_id"] == step["reviewer_id"] or not step["acceptance_criteria"]:
                    raise AgentWorkflowError("Contrôle qualité invalide.")
            seen.add(workflow_id)
            workflows.append({**d, "created_at": event["occurred_at"],
                              "status": "proposal_recorded_not_executed"})
        except (ValueError, KeyError, TypeError):
            rejected += 1
    workflows.sort(key=lambda item: (item["created_at"], item["workflow_id"]))
    return {
        "status": "available" if workflows else "no_recorded_workflows",
        "workflows": workflows, "workflow_count": len(workflows),
        "rejected_events": rejected, "source": "explicit_append_only_audit_events",
        "tasks_created": 0, "assignments_executed": 0, "workers_started": 0,
        "read_only": True,
    }
