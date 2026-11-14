"""Planificateur de synchronisation inter-instances, déterministe et sans écriture.

Ce module transforme un aperçu de réconciliation en plan d'actions référentielles.
Il ne transporte aucun contenu, n'exécute aucun transfert et ne contacte aucun service.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .principal import require_authenticated_agent_principal
from .sync_readiness import SyncReadinessError, build_sync_readiness_report

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_BUCKETS = ("local_only", "remote_only", "identical", "conflicts")
_KINDS = {"memory", "message"}


class SyncProtocolError(ValueError):
    """Plan de synchronisation invalide ou non sûr."""


def _digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_sync_plan(
    *,
    principal: object,
    preview: dict[str, Any],
    destination_instance: str,
    plan_id: str,
    max_actions: int = 500,
) -> dict[str, Any]:
    """Construit un plan de transfert à faire approuver ; aucune écriture n'est possible."""
    actor = require_authenticated_agent_principal(principal).agent_id
    try:
        readiness = build_sync_readiness_report(preview)
    except SyncReadinessError as exc:
        raise SyncProtocolError(str(exc)) from exc

    if preview.get("actor") != actor:
        raise SyncProtocolError("L'aperçu ne correspond pas à l'agent authentifié.")
    if not isinstance(destination_instance, str) or not _IDENTIFIER.fullmatch(destination_instance):
        raise SyncProtocolError("Identifiant d'instance destination invalide.")
    if not isinstance(plan_id, str) or not _IDENTIFIER.fullmatch(plan_id):
        raise SyncProtocolError("Identifiant de plan invalide.")
    if not isinstance(max_actions, int) or isinstance(max_actions, bool) or not 1 <= max_actions <= 500:
        raise SyncProtocolError("La limite doit être comprise entre 1 et 500.")

    candidates: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for bucket in _BUCKETS:
        for row in preview["memory"][bucket] + preview["messages"][bucket]:
            kind, record_id = row["type"], row["record_id"]
            if kind not in _KINDS or not _IDENTIFIER.fullmatch(record_id):
                raise SyncProtocolError("Référence de ressource invalide.")
            key = (kind, record_id)
            if key in seen:
                raise SyncProtocolError("Une ressource apparaît dans plusieurs catégories.")
            seen.add(key)
            if bucket == "local_only":
                candidates.append({"operation": "copy_local_to_remote", "type": kind,
                                   "record_id": record_id})
            elif bucket == "remote_only":
                candidates.append({"operation": "copy_remote_to_local", "type": kind,
                                   "record_id": record_id})

    if len(candidates) > max_actions:
        raise SyncProtocolError("Le plan dépasse la limite d'actions ; réduire le périmètre.")

    actions = []
    for candidate in candidates:
        action_id = _digest({
            "plan_id": plan_id, "actor": actor, "destination": destination_instance,
            **candidate,
        })
        actions.append({"action_id": action_id, **candidate,
                        "status": "pending_human_approval"})

    core = {
        "plan_id": plan_id,
        "actor": actor,
        "destination_instance": destination_instance,
        "source_preview_digest": _digest(preview),
        "actions": actions,
        "conflict_count": preview["counts"]["conflicts"],
        "identical_count": preview["counts"]["identical"],
        "requires_human_approval": bool(actions),
        "conflicts_block_execution": bool(preview["counts"]["conflicts"]),
        "execution_enabled": False,
        "writes_performed": False,
        "mode": "plan_only",
    }
    core["plan_digest"] = _digest(core)
    core["readiness_blockers"] = list(readiness["blockers"])
    core["next_gate"] = (
        "resolve_conflicts_and_obtain_owner_approval"
        if core["conflicts_block_execution"] else
        "owner_approval_and_environment_integration_tests"
    )
    return core


def validate_plan_integrity(plan: dict[str, Any]) -> bool:
    """Vérifie l'intégrité structurelle d'un plan exporté, sans l'autoriser."""
    if not isinstance(plan, dict) or plan.get("mode") != "plan_only":
        raise SyncProtocolError("Un plan en mode plan_only est obligatoire.")
    if plan.get("execution_enabled") is not False or plan.get("writes_performed") is not False:
        raise SyncProtocolError("Un plan ne peut jamais activer l'exécution ou déclarer des écritures.")
    digest = plan.get("plan_digest")
    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise SyncProtocolError("Empreinte du plan absente ou invalide.")
    unsigned = {key: value for key, value in plan.items()
                if key not in {"plan_digest", "readiness_blockers", "next_gate"}}
    if _digest(unsigned) != digest:
        raise SyncProtocolError("L'empreinte du plan ne correspond plus à son contenu.")
    action_ids = [row.get("action_id") for row in plan.get("actions", [])]
    if len(action_ids) != len(set(action_ids)):
        raise SyncProtocolError("Identifiants d'action dupliqués.")
    return True
