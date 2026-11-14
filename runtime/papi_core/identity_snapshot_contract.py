"""Semantic validation for canonical identity snapshots.

This layer validates meaning and cross-field invariants after safe extraction.
It never mutates the supplied snapshots.
"""
from __future__ import annotations

import re
from typing import Any, Iterable


class IdentitySnapshotContractError(ValueError):
    """A snapshot violates the identity semantic contract."""


_AGENT_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,126}[a-z0-9]$|^[a-z0-9]$")
_MAX_STATUS_LENGTH = 64
_MAX_CAPABILITIES = 256
_MAX_CAPABILITY_LENGTH = 160


def _validate_capabilities(value: Any, field: str, agent_id: str) -> list[str]:
    if not isinstance(value, list) or len(value) > _MAX_CAPABILITIES:
        raise IdentitySnapshotContractError(f"{field} invalide pour {agent_id}.")
    seen: set[str] = set()
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or len(item) > _MAX_CAPABILITY_LENGTH:
            raise IdentitySnapshotContractError(f"Élément {field} invalide pour {agent_id}.")
        if item in seen:
            raise IdentitySnapshotContractError(f"Élément {field} dupliqué pour {agent_id}.")
        seen.add(item)
        normalized.append(item)
    return normalized


def _validate_common(
    items: Iterable[dict[str, Any]], *, source: str, id_field: str,
    require_versions: bool,
) -> None:
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise IdentitySnapshotContractError(f"Entrée non objet dans {source}.")
        agent_id = item.get(id_field)
        if not isinstance(agent_id, str) or not _AGENT_ID.fullmatch(agent_id):
            raise IdentitySnapshotContractError(f"Identifiant agent invalide dans {source}.")
        if agent_id in seen_ids:
            raise IdentitySnapshotContractError(f"Identifiant agent dupliqué dans {source}: {agent_id}.")
        seen_ids.add(agent_id)

        status = item.get("status")
        if not isinstance(status, str) or not status.strip() or len(status) > _MAX_STATUS_LENGTH:
            raise IdentitySnapshotContractError(f"Statut invalide pour {agent_id}.")

        permissions = _validate_capabilities(item.get("permissions"), "permissions", agent_id)
        prohibited = _validate_capabilities(item.get("prohibited"), "interdictions", agent_id)
        overlap = set(permissions).intersection(prohibited)
        if overlap:
            raise IdentitySnapshotContractError(
                f"Permission également interdite pour {agent_id}: {sorted(overlap)[0]}."
            )

        if require_versions:
            for field in ("revision", "key_version"):
                value = item.get(field)
                if type(value) is not int or value < 1:
                    raise IdentitySnapshotContractError(f"{field} invalide pour {agent_id}.")


def validate_registry_agents(items: Iterable[dict[str, Any]]) -> None:
    """Validate canonical registry identity, status and capability invariants."""
    _validate_common(items, source="registre canonique", id_field="id", require_versions=False)


def validate_ledger_states(items: Iterable[dict[str, Any]]) -> None:
    """Validate ledger identity, status, positive versions and capability invariants."""
    _validate_common(items, source="ledger transactionnel", id_field="agent_id", require_versions=True)
