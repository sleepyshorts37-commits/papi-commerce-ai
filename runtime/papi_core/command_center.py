"""Vue consolidée en lecture seule pour PAPI COMMAND CENTER."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .astou import build_director_brief
from .audit import read_events
from .agent_history import summarize_agent_history
from .agent_performance import build_agent_performance
from .registry import AGENTS_FILE, TASKS_FILE, load_agents, load_json
from .doctor import diagnose_environment
from .worker_scheduler import build_schedule
from .worker_supervision import build_worker_supervision
from .incident_center import build_incident_center
from .approval_center import build_approval_center
from .identity_security import validate_identity_registry
from .agent_messaging import build_message_center
from .task_delegation import build_delegation_center
from .agent_workflows import build_workflow_center
from .agent_memory import build_memory_center
from .agent_learning import build_agent_learning
from .quality_control import build_quality_control
from .business_intelligence import build_business_intelligence
from .opportunity_scanner import scan_opportunity_signals
from .competitor_intelligence import analyze_competitor_observations
from .product_intelligence import analyze_product_options
from .sales_intelligence import analyze_sales_channels
from .revenue_optimization import optimize_revenue
from .financial_control import build_financial_control
from .procurement import analyze_procurement
from .inventory_control import build_inventory_control
from .order_management import analyze_orders
from .customer_service import analyze_customer_service

ROOT = Path(__file__).resolve().parents[2]
AUDIT_FILE = ROOT / "data" / "events.jsonl"
IDENTITIES_FILE = ROOT / "data" / "agent-identities.json"


def build_command_center(
    tasks_path=TASKS_FILE,
    agents_path=AGENTS_FILE,
    policy_path=None,
    environ=None,
    audit_path=AUDIT_FILE,
    identities_path=IDENTITIES_FILE,
    scheduler_snapshot: dict[str, Any] | None = None,
    supervision_snapshot: dict[str, Any] | None = None,
    opportunity_signals: list[dict[str, Any]] | None = None,
    competitor_observations: list[dict[str, Any]] | None = None,
    product_observations: list[dict[str, Any]] | None = None,
    target_product_selling_price_xof: int | None = None,
    sales_observations: list[dict[str, Any]] | None = None,
    revenue_observations: list[dict[str, Any]] | None = None,
    financial_entries: list[dict[str, Any]] | None = None,
    financial_opening_balances: dict[str, int] | None = None,
    financial_provider_balances: dict[str, int] | None = None,
    procurement_observations: list[dict[str, Any]] | None = None,
    inventory_movements: list[dict[str, Any]] | None = None,
    inventory_opening_stock: dict[str, int] | None = None,
    inventory_reorder_points: dict[str, int] | None = None,
    inventory_target_stock: dict[str, int] | None = None,
    order_records: list[dict[str, Any]] | None = None,
    customer_service_tickets: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Agrège registres et métriques historiques sans modifier les données."""
    agents = load_agents(agents_path)
    tasks_data = load_json(tasks_path)
    tasks = tasks_data.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("'tasks' doit être une liste.")
    valid_tasks = [task for task in tasks if isinstance(task, dict)]
    agent_statuses = Counter(str(agent.get("status", "unknown")) for agent in agents.values())
    task_statuses = Counter(str(task.get("status", "unknown")) for task in valid_tasks)
    brief = build_director_brief(tasks_path, agents_path, policy_path) if policy_path else build_director_brief(tasks_path, agents_path)
    doctor = diagnose_environment(environ)

    scheduler = {
        "status": "not_configured",
        "read_only": True,
        "message": "Aucun instantané de file/worker fourni ; aucune planification calculée.",
        "plan": None,
    }
    if scheduler_snapshot is not None:
        required = {"jobs", "workers", "as_of", "handlers", "policy"}
        if not isinstance(scheduler_snapshot, dict) or set(scheduler_snapshot) != required:
            raise ValueError("scheduler_snapshot doit contenir exactement jobs, workers, as_of, handlers et policy.")
        plan = build_schedule(
            scheduler_snapshot["jobs"],
            scheduler_snapshot["workers"],
            as_of=scheduler_snapshot["as_of"],
            handlers=scheduler_snapshot["handlers"],
            policy=scheduler_snapshot["policy"],
        )
        scheduler = {
            "status": "preview_available",
            "read_only": True,
            "message": "Aperçu calculé à partir de données fournies ; aucune réservation ni exécution.",
            "plan": plan,
        }

    supervision = {
        "status": "not_configured",
        "read_only": True,
        "message": "Aucun instantané de supervision fourni ; aucun diagnostic calculé.",
        "report": None,
    }
    if supervision_snapshot is not None:
        required = {"jobs", "workers", "as_of"}
        optional = {"heartbeat_timeout_seconds", "repeated_failure_threshold"}
        if (not isinstance(supervision_snapshot, dict)
            or not required.issubset(supervision_snapshot)
            or set(supervision_snapshot) - required - optional):
            raise ValueError("supervision_snapshot doit contenir jobs, workers, as_of et éventuellement les deux seuils documentés.")
        options = {key: supervision_snapshot[key] for key in optional if key in supervision_snapshot}
        report = build_worker_supervision(
            supervision_snapshot["jobs"], supervision_snapshot["workers"],
            as_of=supervision_snapshot["as_of"], **options
        )
        supervision = {
            "status": "preview_available",
            "read_only": True,
            "message": "Diagnostic calculé à partir de données fournies ; aucune action de récupération.",
            "report": report,
        }

    events = read_events(audit_path) if audit_path is not None else []
    identity_registry = load_json(identities_path) if identities_path is not None else {"identities": []}
    identity_validation = validate_identity_registry(identity_registry)
    messages = build_message_center(events, identity_registry)
    delegations = build_delegation_center(events, identity_registry)
    workflows = build_workflow_center(events, identity_registry, agents)
    memories = build_memory_center(events, identity_registry)
    learning = build_agent_learning(agents, events, valid_tasks)
    quality_control = build_quality_control(valid_tasks, events)
    effective_policy_path = policy_path or (ROOT / "config" / "policy.json")
    business_policy = load_json(effective_policy_path)
    scanner = scan_opportunity_signals(
        opportunity_signals or [],
        as_of=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    analyzed_candidates = []
    for signal in scanner["signals"]:
        if signal["triage_status"] != "ready_for_business_analysis":
            continue
        analyzed_candidates.append({
            "opportunity_id": signal["signal_id"],
            "source": signal["source"], "source_ref": signal["source_ref"],
            "observed_at": signal["observed_at"], "business_line": signal["business_line"],
            "market": signal["market"], "customer_segment": signal["customer_segment"],
            "offer": signal["offer"],
            "expected_price_xof": signal.get("expected_price_xof"),
            "variable_cost_xof": signal.get("variable_cost_xof"),
            "acquisition_cost_xof": signal.get("acquisition_cost_xof"),
            "fulfillment_cost_xof": signal.get("fulfillment_cost_xof"),
            "estimated_monthly_volume": signal.get("estimated_monthly_volume"),
            "time_to_first_revenue_days": signal.get("time_to_first_revenue_days"),
            "upfront_cost_xof": signal.get("upfront_cost_xof"),
            "evidence_refs": [signal["source_ref"]], "risk_flags": [],
        })
    business_intelligence = build_business_intelligence(analyzed_candidates, business_policy)
    competitor_intelligence = analyze_competitor_observations(
        competitor_observations or [],
        as_of=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    product_intelligence = analyze_product_options(
        product_observations or [],
        as_of=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        target_selling_price_xof=target_product_selling_price_xof,
    )
    sales_intelligence = analyze_sales_channels(
        sales_observations or [],
        as_of=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    revenue_optimization = optimize_revenue(revenue_observations or [])
    financial_control = build_financial_control(
        financial_entries or [], opening_balances=financial_opening_balances,
        provider_balances=financial_provider_balances,
    )
    procurement_intelligence = analyze_procurement(procurement_observations or [], as_of=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))
    inventory_control = build_inventory_control(inventory_movements or [], opening_stock=inventory_opening_stock, reorder_points=inventory_reorder_points, target_stock=inventory_target_stock)
    order_management = analyze_orders(order_records or [], as_of=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))
    customer_service = analyze_customer_service(customer_service_tickets or [], as_of=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))
    incidents = build_incident_center(events)
    approvals = build_approval_center(events)
    performance = build_agent_performance(agents, events, valid_tasks)
    per_agent = {}
    for agent_id in sorted(agents):
        summary = summarize_agent_history(agent_id, events, valid_tasks)
        per_agent[agent_id] = summary["metrics"]
    history_totals = {
        "agents_with_activity": sum(1 for metrics in per_agent.values() if metrics["recorded_events"]),
        "tasks_assigned": sum(metrics["tasks_assigned"] for metrics in per_agent.values()),
        "tasks_completed_by_agent": sum(metrics["tasks_completed_by_agent"] for metrics in per_agent.values()),
        "tasks_blocked_by_agent": sum(metrics["tasks_blocked_by_agent"] for metrics in per_agent.values()),
        "tasks_cancelled_by_agent": sum(metrics["tasks_cancelled_by_agent"] for metrics in per_agent.values()),
        "recorded_events": sum(metrics["recorded_events"] for metrics in per_agent.values()),
    }
    return {
        "product": "PAPI COMMAND CENTER",
        "mode": "read_only_local",
        "dashboard": {
            "agents_total": len(agents),
            "agents_by_status": dict(sorted(agent_statuses.items())),
            "tasks_total": len(valid_tasks),
            "tasks_by_status": dict(sorted(task_statuses.items())),
            "open_tasks": sum(task_statuses.get(status, 0) for status in ("backlog", "ready", "in_progress", "blocked", "review")),
            "pending_approvals": len(brief["owner_escalations"]),
            "unassigned_open_tasks": len(brief["unassigned_tasks"]),
        },
        "agent_history": {
            "status": "available" if events else "no_events",
            "source": "append_only_audit_events",
            "read_only": True,
            "totals": history_totals,
            "by_agent": per_agent,
        },
        "astou_brief": brief,
        "worker_scheduler": scheduler,
        "worker_supervision": supervision,
        "incident_center": incidents,
        "approval_center": approvals,
        "agent_performance": performance,
        "agent_message_center": messages,
        "task_delegation_center": delegations,
        "agent_workflow_center": workflows,
        "agent_memory_center": memories,
        "agent_learning_engine": learning,
        "quality_control_engine": quality_control,
        "opportunity_scanner": scanner,
        "business_intelligence": business_intelligence,
        "competitor_intelligence": competitor_intelligence,
        "product_intelligence": product_intelligence,
        "sales_intelligence": sales_intelligence,
        "revenue_optimization": revenue_optimization,
        "financial_control": financial_control,
        "procurement_intelligence": procurement_intelligence,
        "inventory_control": inventory_control,
        "order_management": order_management,
        "customer_service": customer_service,
        "agent_identity_security": {
            **identity_validation,
            "status": "validated_documentary_registry",
            "runtime_authentication_enabled": False,
            "actions_authorized": 0,
            "actions_executed": 0,
        },
        "environment": {
            "status": doctor["status"],
            "checks": doctor["checks"],
            "network_test_performed": False,
            "secrets_displayed": False,
        },
        "controls": {
            "writes_performed": False,
            "worker_started": False,
            "scheduler_claims_performed": 0,
            "scheduler_handlers_executed": 0,
            "supervision_mutations_performed": 0,
            "supervision_retries_triggered": 0,
            "incident_writes_performed": 0,
            "incident_notifications_sent": 0,
            "approval_writes_performed": 0,
            "approval_actions_executed": 0,
            "message_writes_performed": 0,
            "messages_delivered": 0,
            "task_delegation_writes_performed": 0,
            "task_assignments_executed": 0,
            "workflow_writes_performed": 0,
            "workflow_steps_assigned": 0,
            "memory_writes_performed": 0,
            "memory_shares_performed": 0,
            "learning_records_written": 0,
            "automatic_training_runs": 0,
            "agent_behavior_changes": 0,
            "quality_reviews_created": 0,
            "quality_tasks_changed": 0,
            "business_opportunities_scanned": 0,
            "opportunity_signals_received": scanner["signals_received"],
            "opportunity_signals_rejected": scanner["signals_rejected"],
            "business_plans_created": 0,
            "competitor_observations_received": competitor_intelligence["observations_received"],
            "competitor_observations_rejected": competitor_intelligence["observations_rejected"],
            "product_observations_received": product_intelligence["observations_received"],
            "product_observations_rejected": product_intelligence["observations_rejected"],
            "sales_observations_received": sales_intelligence["observations_received"],
            "sales_observations_rejected": sales_intelligence["observations_rejected"],
            "revenue_observations_received": revenue_optimization["observations_received"],
            "revenue_offers_analyzed": revenue_optimization["offers_analyzed"],
            "revenue_offers_rejected": revenue_optimization["offers_rejected"],
            "prices_changed": 0,
            "commissions_paid": 0,
            "payments_processed": 0,
            "financial_entries_received": financial_control["entries_received"],
            "financial_entries_analyzed": financial_control["entries_analyzed"],
            "financial_entries_rejected": financial_control["entries_rejected"],
            "supplier_observations_received": procurement_intelligence["observations_received"],
            "supplier_observations_analyzed": procurement_intelligence["observations_analyzed"],
            "supplier_observations_rejected": procurement_intelligence["observations_rejected"],
            "live_supplier_searches": 0,
            "suppliers_contacted": 0,
            "purchase_orders_created": 0,
            "purchases_executed": 0,
            "procurement_spending_xof": 0,
            "inventory_movements_received": inventory_control["movements_received"],
            "inventory_movements_analyzed": inventory_control["movements_analyzed"],
            "inventory_movements_rejected": inventory_control["movements_rejected"],
            "replenishment_alerts_created": len(inventory_control["replenishment_alerts"]),
            "stock_records_written": 0,
            "inventory_orders_created": 0,
            "orders_received": order_management["orders_received"],
            "orders_analyzed": order_management["orders_analyzed"],
            "orders_rejected": order_management["orders_rejected"],
            "overdue_orders_detected": len(order_management["overdue_orders"]),
            "order_status_updates_executed": 0,
            "deliveries_dispatched": 0,
            "customer_contacts_sent": 0,
            "customer_service_tickets_received": customer_service["tickets_received"],
            "customer_service_tickets_analyzed": customer_service["tickets_analyzed"],
            "customer_service_tickets_rejected": customer_service["tickets_rejected"],
            "customer_service_drafts_prepared": sum(1 for item in customer_service["tickets"] if item["response_draft"]),
            "customer_service_messages_sent": 0,
            "ledger_writes_performed": 0,
            "transfers_executed": 0,
            "withdrawals_executed": 0,
            "financial_reconciliations_executed": 0,
            "sales_prospects_contacted": 0,
            "sales_campaigns_launched": 0,
            "business_actions_executed": 0,
            "external_actions_enabled": False,
            "financial_actions_enabled": False,
        },
    }
