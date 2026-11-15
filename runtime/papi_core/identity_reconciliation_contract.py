"""Strict, read-only contract for identity reconciliation reports."""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from typing import Any


class IdentityReconciliationReportContractError(ValueError):
    """A reconciliation report violates its versioned integrity contract."""


_REQUIRED_REPORT_FIELDS = {
    "schema_version", "mode", "consistent", "fail_closed",
    "registry_count", "ledger_count", "discrepancy_count",
    "critical_count", "high_count", "discrepancies", "report_sha256",
}
_REQUIRED_DISCREPANCY_FIELDS = {
    "agent_id", "code", "severity", "registry_status", "ledger_status", "message",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise IdentityReconciliationReportContractError(
            "Rapport non sérialisable canoniquement."
        ) from exc


def validate_reconciliation_report(report: Any) -> None:
    """Validate report schema, derived fields, deterministic ordering and digest."""
    if not isinstance(report, dict) or set(report) != _REQUIRED_REPORT_FIELDS:
        raise IdentityReconciliationReportContractError("Schéma du rapport invalide.")
    if type(report["schema_version"]) is not int or report["schema_version"] != 1:
        raise IdentityReconciliationReportContractError("Version de schéma invalide.")
    if report["mode"] != "read_only":
        raise IdentityReconciliationReportContractError("Mode du rapport invalide.")
    for field in ("consistent", "fail_closed"):
        if type(report[field]) is not bool:
            raise IdentityReconciliationReportContractError(f"Indicateur {field} invalide.")
    for field in ("registry_count", "ledger_count", "discrepancy_count",
                  "critical_count", "high_count"):
        if type(report[field]) is not int or report[field] < 0:
            raise IdentityReconciliationReportContractError(f"Compteur {field} invalide.")

    discrepancies = report["discrepancies"]
    if not isinstance(discrepancies, list):
        raise IdentityReconciliationReportContractError("Liste des écarts invalide.")
    seen: set[tuple[str, str]] = set()
    sort_keys: list[tuple[str, str]] = []
    critical = high = 0
    for item in discrepancies:
        if not isinstance(item, dict) or set(item) != _REQUIRED_DISCREPANCY_FIELDS:
            raise IdentityReconciliationReportContractError("Structure d'écart invalide.")
        agent_id, code, severity, message = (
            item["agent_id"], item["code"], item["severity"], item["message"]
        )
        if not isinstance(agent_id, str) or not agent_id:
            raise IdentityReconciliationReportContractError("Identité d'écart invalide.")
        if not isinstance(code, str) or not code:
            raise IdentityReconciliationReportContractError("Code d'écart invalide.")
        if severity not in {"critical", "high"}:
            raise IdentityReconciliationReportContractError("Sévérité d'écart invalide.")
        if not isinstance(message, str) or not message:
            raise IdentityReconciliationReportContractError("Message d'écart invalide.")
        for field in ("registry_status", "ledger_status"):
            if item[field] is not None and not isinstance(item[field], str):
                raise IdentityReconciliationReportContractError(f"{field} invalide.")
        identity_code = (agent_id, code)
        if identity_code in seen:
            raise IdentityReconciliationReportContractError("Écart identité/code dupliqué.")
        seen.add(identity_code)
        sort_keys.append(identity_code)
        if severity == "critical":
            critical += 1
        else:
            high += 1

    if sort_keys != sorted(sort_keys):
        raise IdentityReconciliationReportContractError("Ordre des écarts non déterministe.")
    if report["discrepancy_count"] != len(discrepancies):
        raise IdentityReconciliationReportContractError("Nombre d'écarts incohérent.")
    if report["critical_count"] != critical or report["high_count"] != high:
        raise IdentityReconciliationReportContractError("Compteurs de sévérité incohérents.")
    if report["consistent"] is not (len(discrepancies) == 0):
        raise IdentityReconciliationReportContractError("Indicateur consistent incohérent.")
    if report["fail_closed"] is not (critical > 0):
        raise IdentityReconciliationReportContractError("Indicateur fail_closed incohérent.")

    digest = report["report_sha256"]
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        raise IdentityReconciliationReportContractError("Digest SHA-256 mal formé.")
    payload = {key: value for key, value in report.items() if key != "report_sha256"}
    expected = hashlib.sha256(_canonical(payload)).hexdigest()
    if not hmac.compare_digest(digest, expected):
        raise IdentityReconciliationReportContractError("Digest du rapport invalide.")
