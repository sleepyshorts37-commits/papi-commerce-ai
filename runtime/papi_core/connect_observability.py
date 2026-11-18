"""Local, privacy-minimizing PAPI CONNECT usage ledger and read-only reports."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from .audit import AuditError, append_event, new_event, read_events

MAX_LEDGER_BYTES = 5 * 1024 * 1024
PROVIDER_ID = re.compile(r"^[a-z][a-z0-9._-]{2,63}$")
OPERATION_ID = re.compile(r"^[0-9a-f]{32}$")
ACTIONS = {
    "connector.call.started",
    "connector.call.completed",
    "connector.call.failed",
}


class ConnectorTelemetryError(ValueError):
    """Journal PAPI CONNECT invalide ou indisponible."""


class ConnectorTelemetry:
    """Écrit des métadonnées d'appel sans prompt, sortie ni identifiant de projet.

    Le journal est local, append-only par l'API d'audit existante et limité à
    un seul écrivain. Il ne constitue ni une facture ni un registre financier.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def record(self, action: str, provider_id: str, details: dict[str, Any]) -> None:
        if action not in ACTIONS:
            raise ConnectorTelemetryError("Action de télémétrie inconnue.")
        if not isinstance(provider_id, str) or not PROVIDER_ID.fullmatch(provider_id):
            raise ConnectorTelemetryError("Identifiant fournisseur invalide.")
        if not isinstance(details, dict):
            raise ConnectorTelemetryError("Détails de télémétrie invalides.")
        try:
            event = new_event(
                event_id=uuid4().hex,
                actor="connector-gateway",
                action=action,
                entity_type="provider",
                entity_id=provider_id,
                details=details,
            )
            _validate_connector_event(event)
            payload_size = len(
                (json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
            )
            if self.path.is_symlink():
                raise OSError("Symbolic-link ledger paths are not accepted.")
            current_size = self.path.stat().st_size if self.path.exists() else 0
            if current_size + payload_size > MAX_LEDGER_BYTES:
                raise OSError("Connector telemetry ledger size limit reached.")
            if not append_event(event, self.path):
                raise OSError("Duplicate telemetry event identifier.")
        except Exception:
            # Ne pas propager de diagnostic de système de fichiers au chemin appelant.
            raise ConnectorTelemetryError("Impossible d'enregistrer la télémétrie PAPI CONNECT.") from None


def _require_keys(details: dict[str, Any], expected: set[str]) -> None:
    if set(details) != expected:
        raise ConnectorTelemetryError("Structure de télémétrie invalide.")


def _require_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _validate_connector_event(event: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    action = event["action"]
    provider_id = event["entity_id"]
    details = event["details"]
    if action not in ACTIONS or event["actor"] != "connector-gateway" or event["entity_type"] != "provider":
        raise ConnectorTelemetryError("Événement étranger au journal PAPI CONNECT.")
    if not PROVIDER_ID.fullmatch(provider_id):
        raise ConnectorTelemetryError("Identifiant fournisseur invalide.")
    if not isinstance(details, dict):
        raise ConnectorTelemetryError("Détails de télémétrie invalides.")

    common = {"operation_id", "kind", "estimated_cost_xof"}
    expected = {
        "connector.call.started": common,
        "connector.call.completed": common | {"reported_cost_xof", "duration_ms", "simulated"},
        "connector.call.failed": common | {"duration_ms", "error_code"},
    }[action]
    _require_keys(details, expected)
    if not isinstance(details["operation_id"], str) or not OPERATION_ID.fullmatch(details["operation_id"]):
        raise ConnectorTelemetryError("Identifiant d'opération invalide.")
    if not isinstance(details["kind"], str) or details["kind"] not in {"text", "image"}:
        raise ConnectorTelemetryError("Type de génération invalide.")
    if not _require_nonnegative_int(details["estimated_cost_xof"]):
        raise ConnectorTelemetryError("Estimation de coût invalide.")

    if action != "connector.call.started":
        if not _require_nonnegative_int(details["duration_ms"]):
            raise ConnectorTelemetryError("Durée d'appel invalide.")
    if action == "connector.call.completed":
        if not _require_nonnegative_int(details["reported_cost_xof"]):
            raise ConnectorTelemetryError("Coût déclaré par le fournisseur invalide.")
        if not isinstance(details["simulated"], bool):
            raise ConnectorTelemetryError("Indicateur de simulation invalide.")
    if action == "connector.call.failed" and (
        not isinstance(details["error_code"], str)
        or details["error_code"] not in {"adapter_error", "invalid_result"}
    ):
        raise ConnectorTelemetryError("Code d'erreur de connecteur invalide.")
    return action, provider_id, details


def _empty_totals() -> dict[str, int | float]:
    return {
        "calls_started": 0,
        "calls_completed": 0,
        "calls_failed": 0,
        "calls_incomplete": 0,
        "simulated_completed": 0,
        "non_simulated_completed": 0,
        "estimated_cost_xof": 0,
        "provider_reported_cost_xof": 0,
        "total_duration_ms": 0,
        "average_duration_ms": 0.0,
    }


def _aggregate(operations: list[dict[str, Any]]) -> dict[str, int | float]:
    totals = _empty_totals()
    terminal_durations: list[int] = []
    for operation in operations:
        totals["calls_started"] += 1
        totals["estimated_cost_xof"] += operation["estimated_cost_xof"]
        terminal = operation["terminal"]
        if terminal is None:
            totals["calls_incomplete"] += 1
            continue
        action, details = terminal
        totals["total_duration_ms"] += details["duration_ms"]
        terminal_durations.append(details["duration_ms"])
        if action == "connector.call.failed":
            totals["calls_failed"] += 1
        else:
            totals["calls_completed"] += 1
            totals["provider_reported_cost_xof"] += details["reported_cost_xof"]
            if details["simulated"]:
                totals["simulated_completed"] += 1
            else:
                totals["non_simulated_completed"] += 1
    if terminal_durations:
        totals["average_duration_ms"] = round(
            sum(terminal_durations) / len(terminal_durations), 2
        )
    return totals


def build_connector_usage_report(path: str | Path) -> dict[str, Any]:
    """Construit un agrégat local en lecture seule, sans exposer les événements."""
    ledger_path = Path(path)
    if ledger_path.is_symlink():
        raise ConnectorTelemetryError("Le journal de télémétrie ne doit pas être un lien symbolique.")
    if not ledger_path.exists():
        events: list[dict[str, Any]] = []
    else:
        try:
            if ledger_path.stat().st_size > MAX_LEDGER_BYTES:
                raise ConnectorTelemetryError("Le journal de télémétrie dépasse la taille maximale.")
            events = read_events(ledger_path)
        except ConnectorTelemetryError:
            raise
        except (AuditError, OSError):
            raise ConnectorTelemetryError("Impossible de lire le journal de télémétrie.") from None

    operations: dict[str, dict[str, Any]] = {}
    for event in events:
        action, provider_id, details = _validate_connector_event(event)
        operation_id = details["operation_id"]
        if action == "connector.call.started":
            if operation_id in operations:
                raise ConnectorTelemetryError("Identifiant d'opération dupliqué.")
            operations[operation_id] = {
                "provider_id": provider_id,
                "kind": details["kind"],
                "estimated_cost_xof": details["estimated_cost_xof"],
                "terminal": None,
            }
            continue

        operation = operations.get(operation_id)
        if operation is None:
            raise ConnectorTelemetryError("Événement terminal sans début correspondant.")
        if operation["terminal"] is not None:
            raise ConnectorTelemetryError("Plusieurs événements terminaux pour une opération.")
        if (
            operation["provider_id"] != provider_id
            or operation["kind"] != details["kind"]
            or operation["estimated_cost_xof"] != details["estimated_cost_xof"]
        ):
            raise ConnectorTelemetryError("Métadonnées d'opération incohérentes.")
        operation["terminal"] = (action, details)

    operation_list = list(operations.values())
    totals = _aggregate(operation_list)

    by_provider: dict[str, list[dict[str, Any]]] = {}
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for operation in operation_list:
        by_provider.setdefault(operation["provider_id"], []).append(operation)
        by_kind.setdefault(operation["kind"], []).append(operation)

    return {
        "mode": "local_read_only",
        "events": len(events),
        "totals": totals,
        "by_provider": {
            key: _aggregate(value) for key, value in sorted(by_provider.items())
        },
        "by_kind": {
            key: _aggregate(value) for key, value in sorted(by_kind.items())
        },
        "accounting_note": (
            "Les coûts estimés et déclarés par un adaptateur sont indicatifs ; "
            "ils ne prouvent ni facturation ni paiement."
        ),
        "privacy_note": (
            "Les prompts, sorties, empreintes de contenu, identifiants de projet "
            "et credentials ne figurent pas dans ce rapport."
        ),
    }
