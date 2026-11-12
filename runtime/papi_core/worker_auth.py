"""Authentification cryptographique des opérations de workers PAPI.

Chaque opération mutante est signée par l'identité agent liée au worker.
Ce module authentifie et autorise la requête ; il n'exécute aucun job.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from uuid import UUID

from .agent_identity_auth import (
    AgentIdentityAuthenticationError,
    authenticate_agent_request,
)

class WorkerAuthenticationError(PermissionError):
    """Opération worker non authentifiée ou non autorisée."""

_OPERATION_PERMISSIONS = {
    "claim": "worker.claim_jobs",
    "heartbeat": "worker.heartbeat",
    "complete": "worker.complete",
    "fail": "worker.fail",
}
_ID = re.compile(r"^[A-Za-z0-9_-]{1,120}$")


def authenticate_worker_operation(
    envelope: dict[str, Any],
    *,
    identities_path: Path,
    agents_path: Path,
    public_registry_path: Path,
    replay_db: Path,
) -> dict[str, Any]:
    """Vérifie signature, fraîcheur, anti-rejeu, carte active et périmètre exact.

    Payload signé attendu : operation, worker_id, job_id, lease_token.
    Pour claim, job_id doit être null car le job n'est pas encore connu.
    Le worker_id doit être strictement égal à l'agent_id signataire.
    """
    if not isinstance(envelope, dict) or not isinstance(envelope.get("payload"), dict):
        raise WorkerAuthenticationError("Enveloppe worker invalide : accès fermé.")
    payload = envelope["payload"]
    if set(payload) != {"operation", "worker_id", "job_id", "lease_token"}:
        raise WorkerAuthenticationError("Payload worker invalide : accès fermé.")
    operation = payload.get("operation")
    worker_id = payload.get("worker_id")
    job_id = payload.get("job_id")
    token = payload.get("lease_token")
    agent_id = envelope.get("agent_id")
    if operation not in _OPERATION_PERMISSIONS:
        raise WorkerAuthenticationError("Opération worker inconnue.")
    if not isinstance(agent_id, str) or worker_id != agent_id or not _ID.fullmatch(worker_id or ""):
        raise WorkerAuthenticationError("Identité worker usurpée ou invalide.")
    if operation == "claim":
        if job_id is not None:
            raise WorkerAuthenticationError("Un claim ne peut pas désigner un job non réservé.")
    elif not isinstance(job_id, str) or not _ID.fullmatch(job_id):
        raise WorkerAuthenticationError("job_id invalide pour cette opération.")
    try:
        if not isinstance(token, str) or str(UUID(token)) != token.lower():
            raise ValueError("UUID invalide")
    except (ValueError, TypeError, AttributeError) as exc:
        raise WorkerAuthenticationError("Jeton de bail invalide.") from exc

    try:
        identities = json.loads(Path(identities_path).read_text(encoding="utf-8"))
        cards = [item for item in identities["identities"]
                 if isinstance(item, dict) and item.get("agent_id") == agent_id]
        if len(cards) != 1 or _OPERATION_PERMISSIONS[operation] not in cards[0].get("permissions", []):
            raise WorkerAuthenticationError("Permission worker absente de la carte active.")
        result = authenticate_agent_request(
            envelope, identities_path=identities_path, agents_path=agents_path,
            public_registry_path=public_registry_path, replay_db=replay_db,
        )
    except WorkerAuthenticationError:
        raise
    except (OSError, ValueError, KeyError, TypeError, AgentIdentityAuthenticationError) as exc:
        raise WorkerAuthenticationError("Identité worker non vérifiable : accès fermé.") from exc
    return {
        **result,
        "worker_id": worker_id,
        "operation": operation,
        "job_id": job_id,
        "lease_token_bound": True,
        "permission": _OPERATION_PERMISSIONS[operation],
        "worker_authenticated": True,
    }
