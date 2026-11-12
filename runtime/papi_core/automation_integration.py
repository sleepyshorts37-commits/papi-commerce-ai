"""Adapters between existing PAPI snapshots and the automation planner.

This module reads already-computed in-memory snapshots only. It performs no
network, database, messaging, scheduling, or financial operation.
"""
from __future__ import annotations

from typing import Any, Mapping

from runtime.papi_core.automation_engine import build_automation_plan


def build_plan_from_module_snapshots(
    *,
    sales_pipeline: Mapping[str, Any] | None = None,
    client_manager_snapshot: Mapping[str, Any] | None = None,
    now: str | None = None,
    include_daily_qualification: bool = True,
    include_weekly_report: bool = False,
) -> dict[str, Any]:
    """Translate PAPI Sales Engine and Client Manager outputs into plan inputs.

    Expected sales snapshot is the output of analyze_sales_pipeline(), whose
    validated records use prospect_id and next_follow_up_at.
    Expected client snapshot is the output of analyze_client_manager(), whose
    open cases are exposed as cases.open_case_ids.
    """
    if sales_pipeline is not None and not isinstance(sales_pipeline, Mapping):
        raise ValueError("sales_pipeline doit être un objet.")
    if client_manager_snapshot is not None and not isinstance(client_manager_snapshot, Mapping):
        raise ValueError("client_manager_snapshot doit être un objet.")

    sales_records: list[dict[str, Any]] = []
    if sales_pipeline is not None:
        records = sales_pipeline.get("records", [])
        if not isinstance(records, list):
            raise ValueError("sales_pipeline.records doit être une liste.")
        for record in records:
            if not isinstance(record, Mapping):
                raise ValueError("Chaque prospect doit être un objet.")
            sales_records.append({
                "prospect_ref": record.get("prospect_id"),
                "status": record.get("status"),
                "next_followup_at": record.get("next_follow_up_at"),
            })

    client_cases: list[dict[str, Any]] = []
    if client_manager_snapshot is not None:
        cases = client_manager_snapshot.get("cases", {})
        if not isinstance(cases, Mapping):
            raise ValueError("client_manager_snapshot.cases doit être un objet.")
        open_ids = cases.get("open_case_ids", [])
        if not isinstance(open_ids, list):
            raise ValueError("client_manager_snapshot.cases.open_case_ids doit être une liste.")
        client_cases = [
            {"case_ref": case_id, "status": "open"}
            for case_id in open_ids
            if isinstance(case_id, str) and case_id.strip()
        ]

    plan = build_automation_plan(
        prospects=sales_records,
        client_cases=client_cases,
        now=now,
        include_daily_qualification=include_daily_qualification,
        include_weekly_report=include_weekly_report,
    )
    plan["sources"] = {
        "sales_pipeline_supplied": sales_pipeline is not None,
        "client_manager_supplied": client_manager_snapshot is not None,
        "snapshot_only": True,
    }
    return plan
