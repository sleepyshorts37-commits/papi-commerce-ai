"""Explicit adapters from PAPI AI WORKERS module outputs to dashboard inputs.
No discovery, persistence, network access, notification or workflow execution occurs.
"""
from __future__ import annotations
from typing import Any

class WorkersInputError(ValueError):
    """Invalid or ambiguous PAPI AI WORKERS source data."""

def _batch_results(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        raise WorkersInputError(f"{field} doit être un objet de résultat.")
    results = value.get("results")
    if not isinstance(results, list) or any(not isinstance(item, dict) for item in results):
        raise WorkersInputError(f"{field}.results doit être une liste valide.")
    return results

def _records(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise WorkersInputError(f"{field} doit être une liste valide.")
    return value

def build_workers_inputs(*, platform_discovery_batch=None, handoff_records=None, profitability_batch=None) -> dict[str, Any]:
    """Adapt module outputs; absent sources differ from explicitly empty results."""
    platforms = _batch_results(platform_discovery_batch, "platform_discovery_batch") if platform_discovery_batch is not None else []
    handoffs = _records(handoff_records, "handoff_records") if handoff_records is not None else []
    profitability = _batch_results(profitability_batch, "profitability_batch") if profitability_batch is not None else []
    return {
        "platform_candidates": platforms,
        "handoffs": handoffs,
        "profitability_results": profitability,
        "sources": {
            "platform_discovery_supplied": platform_discovery_batch is not None,
            "human_handoffs_supplied": handoff_records is not None,
            "profitability_supplied": profitability_batch is not None,
            "automatic_collection_performed": False,
            "persistent_storage_read": False,
            "network_access_performed": False,
        },
    }
