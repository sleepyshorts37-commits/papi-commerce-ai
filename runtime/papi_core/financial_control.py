"""Read-only cash ledger, expense/revenue tracking and balance reconciliation."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

DIRECTIONS = {"inflow", "outflow"}
CATEGORIES = {"sale", "service", "affiliate_commission", "partner_commission",
              "operating_expense", "product_purchase", "delivery", "refund",
              "payment_fee", "tax", "owner_contribution", "owner_withdrawal",
              "commission_payout", "other"}
METHODS = {"wave", "orange_money", "cash", "bank", "paypal", "card", "other"}


class FinancialControlError(ValueError):
    """Invalid ledger or reconciliation input."""


def _amount(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise FinancialControlError(f"{field} doit être un montant entier XOF positif ou nul.")
    return value


def _text(value: Any, field: str, limit: int = 180) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise FinancialControlError(f"{field} doit être un texte non vide ({limit} caractères maximum).")
    result = value.strip()
    lowered = result.lower()
    if "@" in result or any(x in lowered for x in ("password", "token=", "api_key", "secret")):
        raise FinancialControlError(f"{field} contient une donnée sensible interdite.")
    return result


def _date(value: Any) -> datetime:
    if not isinstance(value, str):
        raise FinancialControlError("occurred_at doit être une date ISO 8601 avec fuseau.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FinancialControlError("occurred_at invalide.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise FinancialControlError("occurred_at doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)


def build_financial_control(
    entries: list[dict[str, Any]], *,
    opening_balances: dict[str, int] | None = None,
    provider_balances: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Project user-supplied aggregate ledger records; never moves money or writes."""
    if not isinstance(entries, list):
        raise FinancialControlError("entries doit être une liste.")
    opening_balances = opening_balances or {}
    provider_balances = provider_balances or {}
    if not isinstance(opening_balances, dict) or not isinstance(provider_balances, dict):
        raise FinancialControlError("Les soldes doivent être des objets compte:montant.")
    opening = {_text(k, "account"): _amount(v, "opening_balance") for k, v in opening_balances.items()}
    provider = {_text(k, "account"): _amount(v, "provider_balance") for k, v in provider_balances.items()}
    rows, rejected, seen = [], [], set()
    verified_in = verified_out = pending_in = pending_out = 0
    by_account: dict[str, dict[str, int]] = {}
    by_category: dict[str, dict[str, int]] = {}
    by_month: dict[str, dict[str, int]] = {}
    for index, raw in enumerate(entries):
        try:
            required = {"entry_ref", "account", "direction", "category", "amount_xof",
                        "status", "occurred_at", "payment_method"}
            optional = {"business_line", "note"}
            if not isinstance(raw, dict) or not required.issubset(raw) or set(raw) - required - optional:
                raise FinancialControlError("Champs obligatoires manquants ou champs inconnus.")
            ref = _text(raw["entry_ref"], "entry_ref")
            account = _text(raw["account"], "account")
            direction = _text(raw["direction"], "direction")
            category = _text(raw["category"], "category")
            status = _text(raw["status"], "status")
            method = _text(raw["payment_method"], "payment_method")
            if direction not in DIRECTIONS or category not in CATEGORIES:
                raise FinancialControlError("direction ou category non reconnue.")
            if status not in {"verified", "declared", "pending"}:
                raise FinancialControlError("status doit être verified, declared ou pending.")
            if method not in METHODS:
                raise FinancialControlError("payment_method non reconnu.")
            amount = _amount(raw["amount_xof"], "amount_xof")
            occurred = _date(raw["occurred_at"])
            line = raw.get("business_line")
            if line is not None:
                line = _text(line, "business_line")
            note = raw.get("note", "")
            if not isinstance(note, str) or len(note) > 300 or "@" in note:
                raise FinancialControlError("note invalide ou contenant une donnée personnelle.")
            key = (ref, account)
            if key in seen:
                raise FinancialControlError("entry_ref déjà utilisé pour ce compte.")
            seen.add(key)
            month = occurred.strftime("%Y-%m")
            rows.append({"entry_ref": ref, "account": account, "direction": direction,
                         "category": category, "amount_xof": amount, "status": status,
                         "occurred_at": occurred.isoformat().replace("+00:00", "Z"),
                         "month": month, "payment_method": method,
                         "business_line": line, "note": note,
                         "cash_effect": "included_in_verified_balance" if status == "verified" else "excluded_pending_verification"})
            bucket = by_account.setdefault(account, {"verified_inflow_xof": 0,
                "verified_outflow_xof": 0, "pending_inflow_xof": 0, "pending_outflow_xof": 0})
            cat = by_category.setdefault(category, {"verified_inflow_xof": 0,
                "verified_outflow_xof": 0, "pending_inflow_xof": 0, "pending_outflow_xof": 0})
            monthly = by_month.setdefault(month, {"verified_inflow_xof": 0,
                "verified_outflow_xof": 0, "pending_inflow_xof": 0, "pending_outflow_xof": 0})
            suffix = "inflow" if direction == "inflow" else "outflow"
            prefix = "verified" if status == "verified" else "pending"
            field = f"{prefix}_{suffix}_xof"
            bucket[field] += amount
            cat[field] += amount
            monthly[field] += amount
            if status == "verified":
                if direction == "inflow":
                    verified_in += amount
                else:
                    verified_out += amount
            elif direction == "inflow":
                pending_in += amount
            else:
                pending_out += amount
        except (FinancialControlError, TypeError, KeyError) as exc:
            rejected.append({"index": index, "reason": str(exc)})
    accounts = sorted(set(by_account) | set(opening) | set(provider))
    balances = {}
    for account in accounts:
        stats = by_account.get(account, {})
        start = opening.get(account, 0)
        calculated = start + stats.get("verified_inflow_xof", 0) - stats.get("verified_outflow_xof", 0)
        external = provider.get(account)
        balances[account] = {
            "opening_balance_xof": start,
            "verified_inflow_xof": stats.get("verified_inflow_xof", 0),
            "verified_outflow_xof": stats.get("verified_outflow_xof", 0),
            "calculated_verified_balance_xof": calculated,
            "provider_reported_balance_xof": external,
            "reconciliation_difference_xof": calculated - external if external is not None else None,
            "reconciliation_status": ("matched" if calculated == external else "mismatch") if external is not None else "not_provided",
            "pending_inflow_excluded_xof": stats.get("pending_inflow_xof", 0),
            "pending_outflow_excluded_xof": stats.get("pending_outflow_xof", 0),
        }
    return {
        "status": "available" if rows else "no_valid_ledger_entries",
        "currency": "XOF", "source": "user_supplied_aggregate_ledger_entries",
        "entries_received": len(entries), "entries_analyzed": len(rows),
        "entries_rejected": len(rejected), "entries": rows, "rejected": rejected,
        "totals": {"verified_inflow_xof": verified_in, "verified_outflow_xof": verified_out,
                   "verified_net_cash_movement_xof": verified_in - verified_out,
                   "pending_inflow_xof": pending_in, "pending_outflow_xof": pending_out,
                   "pending_net_xof": pending_in - pending_out},
        "balances_by_account": balances,
        "totals_by_category": by_category, "totals_by_month": by_month,
        "commission_tracking": {
            "verified_commission_payouts_xof": sum(r["amount_xof"] for r in rows
                if r["status"] == "verified" and r["direction"] == "outflow"
                and r["category"] == "commission_payout"),
            "declared_or_pending_commission_payouts_xof": sum(r["amount_xof"] for r in rows
                if r["status"] != "verified" and r["direction"] == "outflow"
                and r["category"] == "commission_payout"),
            "commission_earned_is_not_inferred": True,
        },
        "limitations": [
            "verified means the supplied record is asserted as reconciled by its provider; this engine does not contact providers or inspect statements.",
            "Only verified entries affect calculated balances; declared and pending entries remain separate.",
            "Opening balances and provider balances are user-supplied snapshots, not independently authenticated.",
            "No customer identities, account numbers, transaction identifiers, credentials or card details are accepted.",
            "This is a cash-movement view, not audited accounting, tax advice or a complete profit-and-loss statement.",
        ],
        "controls": {"read_only": True, "ledger_writes": 0, "payments_processed": 0,
                     "transfers_executed": 0, "withdrawals_executed": 0,
                     "commissions_paid": 0, "external_requests": 0, "spending_xof": 0},
    }
