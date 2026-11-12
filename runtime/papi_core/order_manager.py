"""PAPI ORDER MANAGER 1.59: privacy-minimized order lifecycle tracking."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

STATUSES = {"draft", "confirmed", "preparing", "ready", "dispatched", "delivered", "cancelled", "returned"}
TRANSITIONS = {
    "draft": {"confirmed", "cancelled"},
    "confirmed": {"preparing", "cancelled"},
    "preparing": {"ready", "cancelled"},
    "ready": {"dispatched", "cancelled"},
    "dispatched": {"delivered"},
    "delivered": {"returned"},
    "cancelled": set(),
    "returned": set(),
}
FIELDS = {"order_id", "client_ref", "business_unit", "order_summary", "status",
          "created_at", "updated_at", "status_history", "related_quote_id"}
MAX_RECORDS = 500


def _date(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} doit être une date ISO 8601.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} doit être une date ISO 8601.") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)


def _text(value: Any, field: str, limit: int = 120) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ValueError(f"{field} invalide.")
    return value.strip()


def _normalize(raw: Any, now: datetime) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("Chaque commande doit être un objet.")
    if set(raw) - FIELDS:
        raise ValueError("Champ inconnu ou donnée personnelle interdite dans la commande.")
    required = {"order_id", "client_ref", "business_unit", "order_summary",
                "status", "created_at", "updated_at", "status_history"}
    if not required.issubset(raw):
        raise ValueError("Champs obligatoires manquants dans la commande.")

    created = _date(raw["created_at"], "created_at")
    updated = _date(raw["updated_at"], "updated_at")
    if updated < created:
        raise ValueError("updated_at ne peut pas précéder created_at.")
    if created > now or updated > now:
        raise ValueError("Les dates de commande ne peuvent pas être dans le futur.")

    history = raw["status_history"]
    if not isinstance(history, list) or not 1 <= len(history) <= 20:
        raise ValueError("status_history doit contenir entre 1 et 20 événements.")
    clean_history = []
    previous_status = None
    previous_at = None
    for index, event in enumerate(history):
        if not isinstance(event, dict) or set(event) != {"status", "at"}:
            raise ValueError("Chaque événement doit contenir uniquement status et at.")
        status = event["status"]
        if status not in STATUSES:
            raise ValueError("Statut de commande inconnu dans l'historique.")
        at = _date(event["at"], f"status_history[{index}].at")
        if at > now:
            raise ValueError("Un événement de statut ne peut pas être dans le futur.")
        if index == 0:
            if status != "draft" or at != created:
                raise ValueError("L'historique doit commencer par draft à created_at.")
        elif status not in TRANSITIONS[previous_status]:
            raise ValueError(f"Transition interdite : {previous_status} vers {status}.")
        if previous_at is not None and at < previous_at:
            raise ValueError("Les dates de l'historique doivent être chronologiques.")
        clean_history.append({"status": status, "at": at.isoformat()})
        previous_status, previous_at = status, at

    if previous_status != raw["status"]:
        raise ValueError("Le statut courant doit correspondre au dernier événement.")
    if previous_at != updated:
        raise ValueError("updated_at doit correspondre à la date du dernier événement.")
    if raw["status"] == "draft" and len(history) != 1:
        raise ValueError("Une commande draft ne peut avoir qu'un seul événement.")

    summary = raw["order_summary"]
    if not isinstance(summary, str) or not summary.strip() or len(summary.strip()) > 1000:
        raise ValueError("order_summary invalide.")

    quote_id = raw.get("related_quote_id")
    if quote_id is not None:
        quote_id = _text(quote_id, "related_quote_id")

    return {
        "order_id": _text(raw["order_id"], "order_id"),
        "client_ref": _text(raw["client_ref"], "client_ref"),
        "business_unit": _text(raw["business_unit"], "business_unit"),
        "order_summary": summary.strip(),
        "status": raw["status"],
        "created_at": created.isoformat(),
        "updated_at": updated.isoformat(),
        "status_history": clean_history,
        "related_quote_id": quote_id,
    }


def analyze_orders(records: list[dict], *, as_of: str | None = None) -> dict:
    """Validate minimized order snapshots and report operational queues; no execution."""
    if not isinstance(records, list):
        raise ValueError("records doit être une liste.")
    if len(records) > MAX_RECORDS:
        raise ValueError(f"Maximum de {MAX_RECORDS} commandes.")
    now = _date(as_of or datetime.now(timezone.utc).isoformat(), "as_of")
    valid, rejected, seen = [], [], set()
    for index, raw in enumerate(records):
        try:
            item = _normalize(raw, now)
            if item["order_id"] in seen:
                raise ValueError("order_id dupliqué.")
            seen.add(item["order_id"])
            valid.append(item)
        except (ValueError, TypeError, KeyError) as exc:
            rejected.append({"index": index, "reason": str(exc)})

    counts = {status: sum(item["status"] == status for item in valid) for status in sorted(STATUSES)}
    active = [item["order_id"] for item in valid
              if item["status"] not in {"delivered", "cancelled", "returned"}]
    delayed = [item["order_id"] for item in valid
               if item["status"] == "dispatched" and
               (now - _date(item["updated_at"], "updated_at")).total_seconds() >= 48 * 3600]
    return {
        "as_of": now.isoformat(),
        "counts": {"valid": len(valid), "rejected": len(rejected), "by_status": counts},
        "queues": {"active_order_ids": active, "dispatched_48h_or_more": delayed},
        "orders": valid,
        "rejected": rejected,
        "safety": {
            "read_only": True, "external_orders_created": False,
            "client_contact": False, "messages_sent": False,
            "payments_or_refunds": False, "personal_contact_data_stored": False,
            "budget_xof": 0, "human_review_required": True,
            "note": "Références client pseudonymisées uniquement. Ce module suit les commandes déclarées; il ne contacte aucun client, fournisseur ou livreur."
        },
    }
