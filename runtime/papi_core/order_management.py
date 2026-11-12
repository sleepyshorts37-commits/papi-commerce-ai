"""Read-only order intake, lifecycle checks and delivery-delay detection."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

STATUSES = {
    "draft", "pending_payment", "paid", "processing", "ready_to_ship",
    "shipped", "delivered", "cancelled", "refunded", "on_hold",
}
PAYMENT_EVIDENCE = {"unknown", "pending", "declared_paid", "provider_confirmed", "unpaid", "refunded"}
ALLOWED_FIELDS = {
    "order_id", "business_line", "channel", "created_at", "updated_at", "status",
    "expected_delivery_at", "delivered_at", "payment_evidence_status",
    "total_xof", "currency", "items",
}


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} doit être une date ISO 8601.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} doit être une date ISO 8601.") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)


def _validate_order(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("Chaque commande doit être un objet.")
    extra = set(record) - ALLOWED_FIELDS
    if extra:
        raise ValueError("Champs non autorisés (données personnelles ou champ inconnu).")
    required = {"order_id", "business_line", "channel", "created_at", "updated_at", "status"}
    if not required.issubset(record):
        raise ValueError("Champs obligatoires manquants.")
    for field in ("order_id", "business_line", "channel"):
        value = record[field]
        if not isinstance(value, str) or not value.strip() or len(value) > 100:
            raise ValueError(f"{field} invalide.")
    if record["status"] not in STATUSES:
        raise ValueError("Statut de commande inconnu.")
    created = _timestamp(record["created_at"], "created_at")
    updated = _timestamp(record["updated_at"], "updated_at")
    if updated < created:
        raise ValueError("updated_at ne peut pas précéder created_at.")
    expected = _timestamp(record["expected_delivery_at"], "expected_delivery_at") if record.get("expected_delivery_at") else None
    delivered = _timestamp(record["delivered_at"], "delivered_at") if record.get("delivered_at") else None
    if expected and expected < created:
        raise ValueError("expected_delivery_at ne peut pas précéder created_at.")
    if delivered and (delivered < created or delivered > updated):
        raise ValueError("delivered_at doit être compris entre created_at et updated_at.")
    if record["status"] == "delivered" and delivered is None:
        raise ValueError("Une commande livrée doit avoir delivered_at.")
    payment = record.get("payment_evidence_status", "unknown")
    if payment not in PAYMENT_EVIDENCE:
        raise ValueError("payment_evidence_status invalide.")
    amount = record.get("total_xof")
    if amount is not None and (isinstance(amount, bool) or not isinstance(amount, int) or amount < 0):
        raise ValueError("total_xof doit être un entier positif ou nul.")
    currency = record.get("currency", "XOF")
    if currency != "XOF":
        raise ValueError("Seule la devise XOF est acceptée.")
    items = record.get("items", [])
    if not isinstance(items, list):
        raise ValueError("items doit être une liste.")
    clean_items = []
    for item in items:
        if not isinstance(item, dict) or set(item) != {"sku", "quantity"}:
            raise ValueError("Chaque article doit contenir uniquement sku et quantity.")
        if not isinstance(item["sku"], str) or not item["sku"].strip() or len(item["sku"]) > 100:
            raise ValueError("SKU invalide.")
        qty = item["quantity"]
        if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
            raise ValueError("La quantité doit être un entier strictement positif.")
        clean_items.append({"sku": item["sku"].strip(), "quantity": qty})
    return {
        "order_id": record["order_id"].strip(),
        "business_line": record["business_line"].strip(),
        "channel": record["channel"].strip(),
        "created_at": created.isoformat(),
        "updated_at": updated.isoformat(),
        "status": record["status"],
        "expected_delivery_at": expected.isoformat() if expected else None,
        "delivered_at": delivered.isoformat() if delivered else None,
        "payment_evidence_status": payment,
        "total_xof": amount,
        "currency": "XOF",
        "items": clean_items,
    }


def analyze_orders(
    records: list[dict[str, Any]],
    *,
    as_of: str | None = None,
    stale_after_hours: int = 48,
) -> dict[str, Any]:
    """Analyze supplied order snapshots only; never changes order state or contacts anyone."""
    if not isinstance(records, list):
        raise ValueError("records doit être une liste.")
    if isinstance(stale_after_hours, bool) or not isinstance(stale_after_hours, int) or stale_after_hours < 1:
        raise ValueError("stale_after_hours doit être un entier positif.")
    now = _timestamp(as_of or datetime.now(timezone.utc).isoformat(), "as_of")
    orders, rejected, seen = [], [], set()
    for index, record in enumerate(records):
        try:
            order = _validate_order(record)
            if order["order_id"] in seen:
                raise ValueError("Identifiant de commande dupliqué.")
            seen.add(order["order_id"])
            updated = _timestamp(order["updated_at"], "updated_at")
            expected = _timestamp(order["expected_delivery_at"], "expected_delivery_at") if order["expected_delivery_at"] else None
            delivered = order["status"] == "delivered"
            terminal = order["status"] in {"delivered", "cancelled", "refunded"}
            overdue = bool(expected and expected < now and not terminal)
            stale = (now - updated).total_seconds() > stale_after_hours * 3600 and not terminal
            order["delivery_delay_detected"] = overdue
            order["stale_update_detected"] = stale
            orders.append(order)
        except (TypeError, ValueError) as exc:
            rejected.append({"index": index, "reason": str(exc)})
    counts: dict[str, int] = {}
    for status in sorted(STATUSES):
        counts[status] = sum(order["status"] == status for order in orders)
    return {
        "status": "analyzed" if orders else ("rejected" if rejected else "empty"),
        "read_only": True,
        "orders_received": len(records),
        "orders_analyzed": len(orders),
        "orders_rejected": len(rejected),
        "orders_by_status": counts,
        "overdue_orders": [o["order_id"] for o in orders if o["delivery_delay_detected"]],
        "stale_orders": [o["order_id"] for o in orders if o["stale_update_detected"]],
        "orders": orders,
        "rejections": rejected,
        "financial_note": "total_xof représente une valeur de commande déclarée, pas un chiffre d'affaires encaissé. payment_evidence_status n'est pas authentifié par un prestataire.",
        "limitations": [
            "Les instantanés sont fournis par l'appelant et ne sont pas vérifiés auprès d'une plateforme.",
            "Aucune donnée personnelle client n'est acceptée.",
            "Aucun statut n'est modifié et aucune livraison, notification ou opération financière n'est exécutée.",
        ],
    }
