"""Read-only reconciliation between the canonical agent registry and identity ledger."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable


class IdentityReconciliationError(ValueError):
    """Input snapshots are malformed or ambiguous."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _index_agents(items: Iterable[dict[str, Any]], source: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            raise IdentityReconciliationError(f"Entrée invalide dans {source}.")
        agent_id = item.get("id") if source == "registry" else item.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise IdentityReconciliationError(f"Identifiant absent dans {source}.")
        if agent_id in indexed:
            raise IdentityReconciliationError(f"Identifiant dupliqué dans {source}: {agent_id}.")
        indexed[agent_id] = item
    return indexed


def reconcile_identity_snapshots(
    registry_agents: Iterable[dict[str, Any]],
    ledger_states: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Compare snapshots without writing, activating, revoking or changing permissions.

    Registry statuses 'active' and 'revoked' are lifecycle states. Other statuses
    (planned/defined/design_and_scaffold) are not evidence of runtime activation.
    """
    registry = _index_agents(registry_agents, "registry")
    ledger = _index_agents(ledger_states, "ledger")
    discrepancies: list[dict[str, Any]] = []

    for agent_id in sorted(set(registry) | set(ledger)):
        canonical = registry.get(agent_id)
        state = ledger.get(agent_id)
        if canonical is None:
            discrepancies.append({
                "agent_id": agent_id, "code": "LEDGER_ORPHAN",
                "severity": "critical", "registry_status": None,
                "ledger_status": state.get("status"),
                "message": "État transactionnel sans identité dans le registre canonique.",
            })
            continue
        if state is None:
            if canonical.get("status") in {"active", "revoked"}:
                discrepancies.append({
                    "agent_id": agent_id, "code": "LEDGER_MISSING",
                    "severity": "critical", "registry_status": canonical.get("status"),
                    "ledger_status": None,
                    "message": "Identité canonique en cycle de vie sans état transactionnel.",
                })
            continue

        registry_status = canonical.get("status")
        ledger_status = state.get("status")
        if registry_status not in {"active", "revoked"}:
            discrepancies.append({
                "agent_id": agent_id, "code": "UNAUTHORIZED_LEDGER_ACTIVATION",
                "severity": "critical", "registry_status": registry_status,
                "ledger_status": ledger_status,
                "message": "Le registre canonique ne déclare pas cette identité active ou révoquée.",
            })
        elif registry_status != ledger_status:
            discrepancies.append({
                "agent_id": agent_id, "code": "STATUS_MISMATCH",
                "severity": "critical", "registry_status": registry_status,
                "ledger_status": ledger_status,
                "message": "Les états canoniques et transactionnels divergent.",
            })

        canonical_permissions = canonical.get("permissions")
        canonical_prohibited = canonical.get("prohibited")
        if canonical_permissions is not None and sorted(set(canonical_permissions)) != sorted(set(state.get("permissions", []))):
            discrepancies.append({
                "agent_id": agent_id, "code": "PERMISSIONS_MISMATCH",
                "severity": "high", "registry_status": registry_status,
                "ledger_status": ledger_status,
                "message": "Les permissions déclarées divergent entre les deux registres.",
            })
        if canonical_prohibited is not None and sorted(set(canonical_prohibited)) != sorted(set(state.get("prohibited", []))):
            discrepancies.append({
                "agent_id": agent_id, "code": "PROHIBITIONS_MISMATCH",
                "severity": "critical", "registry_status": registry_status,
                "ledger_status": ledger_status,
                "message": "Les interdictions divergent entre les deux registres.",
            })
        if type(state.get("revision")) is not int or state["revision"] < 1:
            discrepancies.append({
                "agent_id": agent_id, "code": "INVALID_REVISION",
                "severity": "critical", "registry_status": registry_status,
                "ledger_status": ledger_status,
                "message": "Révision transactionnelle invalide.",
            })
        if type(state.get("key_version")) is not int or state["key_version"] < 1:
            discrepancies.append({
                "agent_id": agent_id, "code": "INVALID_KEY_VERSION",
                "severity": "critical", "registry_status": registry_status,
                "ledger_status": ledger_status,
                "message": "Version de clé transactionnelle invalide.",
            })

    discrepancies.sort(key=lambda item: (item["agent_id"], item["code"]))
    critical = sum(item["severity"] == "critical" for item in discrepancies)
    high = sum(item["severity"] == "high" for item in discrepancies)
    report = {
        "schema_version": 1,
        "mode": "read_only",
        "consistent": not discrepancies,
        "fail_closed": bool(critical),
        "registry_count": len(registry),
        "ledger_count": len(ledger),
        "discrepancy_count": len(discrepancies),
        "critical_count": critical,
        "high_count": high,
        "discrepancies": discrepancies,
    }
    report["report_sha256"] = hashlib.sha256(_canonical(report)).hexdigest()
    return report
