"""Strict, bounded JSON ingestion for identity reconciliation reports."""
from __future__ import annotations

import json
from typing import Any

from .identity_reconciliation_contract import (
    IdentityReconciliationReportContractError,
    validate_reconciliation_report,
)


class IdentityReconciliationArtifactError(ValueError):
    """An untrusted serialized reconciliation report cannot be accepted."""


MAX_RECONCILIATION_REPORT_BYTES = 2 * 1024 * 1024


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise IdentityReconciliationArtifactError("Clé JSON dupliquée.")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise IdentityReconciliationArtifactError(
        "Constante numérique JSON non standard interdite."
    )


def load_reconciliation_report(raw: bytes) -> dict[str, Any]:
    """Parse and validate an untrusted JSON report from bounded UTF-8 bytes."""
    if not isinstance(raw, bytes):
        raise IdentityReconciliationArtifactError("Le rapport doit être fourni en octets.")
    if len(raw) > MAX_RECONCILIATION_REPORT_BYTES:
        raise IdentityReconciliationArtifactError("Rapport sérialisé trop volumineux.")
    try:
        document = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
    except IdentityReconciliationArtifactError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise IdentityReconciliationArtifactError(
            "Rapport JSON illisible ou invalide."
        ) from exc

    if not isinstance(document, dict):
        raise IdentityReconciliationArtifactError(
            "La racine du rapport doit être un objet JSON."
        )
    try:
        validate_reconciliation_report(document)
    except IdentityReconciliationReportContractError as exc:
        raise IdentityReconciliationArtifactError(
            "Le rapport ne respecte pas le contrat d'intégrité."
        ) from exc
    return document


def canonicalize_reconciliation_report(report: Any) -> bytes:
    """Return stable canonical JSON bytes for a valid report without mutating it."""
    try:
        validate_reconciliation_report(report)
        return json.dumps(
            report,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except IdentityReconciliationReportContractError as exc:
        raise IdentityReconciliationArtifactError(
            "Le rapport ne respecte pas le contrat d'intégrité."
        ) from exc
    except (TypeError, ValueError, UnicodeError) as exc:
        raise IdentityReconciliationArtifactError(
            "Le rapport ne peut pas être sérialisé canoniquement."
        ) from exc
