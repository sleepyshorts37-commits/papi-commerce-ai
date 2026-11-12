"""Read-only customer-service ticket triage and human-review draft suggestions."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

STATUSES = {"new", "open", "waiting_customer", "waiting_internal", "resolved", "closed"}
CATEGORIES = {"order_status", "delivery_delay", "payment_question", "product_question", "return_refund", "complaint", "technical_issue", "other"}
PRIORITIES = {"low", "normal", "high", "urgent"}
FIELDS = {"ticket_id", "business_line", "channel", "created_at", "updated_at", "status", "category", "priority", "order_ref", "redacted_summary"}


def _date(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} doit être une date ISO 8601.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} doit être une date ISO 8601.") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} doit inclure un fuseau horaire.")
    return parsed.astimezone(timezone.utc)


def _validate(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("Chaque ticket doit être un objet.")
    if set(record) - FIELDS:
        raise ValueError("Champ non autorisé : ne pas transmettre de données personnelles ni de conversation brute.")
    required = {"ticket_id", "business_line", "channel", "created_at", "updated_at", "status", "category", "priority"}
    if not required.issubset(record):
        raise ValueError("Champs obligatoires manquants.")
    for key in ("ticket_id", "business_line", "channel"):
        if not isinstance(record[key], str) or not record[key].strip() or len(record[key]) > 100:
            raise ValueError(f"{key} invalide.")
    if record["status"] not in STATUSES or record["category"] not in CATEGORIES or record["priority"] not in PRIORITIES:
        raise ValueError("Statut, catégorie ou priorité invalide.")
    created, updated = _date(record["created_at"], "created_at"), _date(record["updated_at"], "updated_at")
    if updated < created:
        raise ValueError("updated_at ne peut pas précéder created_at.")
    ref = record.get("order_ref")
    if ref is not None and (not isinstance(ref, str) or not ref.strip() or len(ref) > 100):
        raise ValueError("order_ref invalide.")
    summary = record.get("redacted_summary", "")
    if not isinstance(summary, str) or len(summary) > 500:
        raise ValueError("redacted_summary doit être un texte expurgé de 500 caractères maximum.")
    return {
        "ticket_id": record["ticket_id"].strip(), "business_line": record["business_line"].strip(),
        "channel": record["channel"].strip(), "created_at": created.isoformat(),
        "updated_at": updated.isoformat(), "status": record["status"],
        "category": record["category"], "priority": record["priority"],
        "order_ref": ref.strip() if ref else None, "redacted_summary": summary,
    }


def _draft(category: str) -> str:
    drafts = {
        "order_status": "Bonjour, nous vérifions le statut de votre commande. Nous vous communiquerons une mise à jour après vérification.",
        "delivery_delay": "Bonjour, nous vérifions l'avancement de la livraison et revenons vers vous avec une information confirmée.",
        "payment_question": "Bonjour, nous allons vérifier les informations de paiement avant de vous confirmer le statut.",
        "product_question": "Bonjour, merci pour votre intérêt. Nous vérifions les caractéristiques et disponibilités afin de vous répondre précisément.",
        "return_refund": "Bonjour, nous examinons votre demande selon les conditions applicables. Aucune validation de retour ou de remboursement n'est encore effectuée.",
        "complaint": "Bonjour, nous avons pris note de votre réclamation. Elle sera examinée par un responsable afin de vous apporter une réponse adaptée.",
        "technical_issue": "Bonjour, nous analysons le problème signalé. Merci de ne transmettre aucun mot de passe ni code de sécurité.",
        "other": "Bonjour, votre demande nécessite une vérification complémentaire. Elle sera orientée vers le service compétent.",
    }
    return drafts[category]


def analyze_customer_service(
    records: list[dict[str, Any]],
    *,
    as_of: str | None = None,
    stale_after_hours: int = 24,
) -> dict[str, Any]:
    """Validate anonymized ticket summaries and prepare drafts for human review only."""
    if not isinstance(records, list):
        raise ValueError("records doit être une liste.")
    if isinstance(stale_after_hours, bool) or not isinstance(stale_after_hours, int) or stale_after_hours < 1:
        raise ValueError("stale_after_hours doit être un entier positif.")
    now = _date(as_of or datetime.now(timezone.utc).isoformat(), "as_of")
    tickets, rejected, seen = [], [], set()
    for index, raw in enumerate(records):
        try:
            ticket = _validate(raw)
            if ticket["ticket_id"] in seen:
                raise ValueError("Identifiant de ticket dupliqué.")
            seen.add(ticket["ticket_id"])
            updated = _date(ticket["updated_at"], "updated_at")
            age_hours = max(0, int((now - updated).total_seconds() // 3600))
            active = ticket["status"] not in {"resolved", "closed"}
            ticket["age_since_update_hours"] = age_hours
            ticket["stale_update_detected"] = active and age_hours > stale_after_hours
            ticket["response_draft"] = _draft(ticket["category"]) if active else None
            ticket["human_review_required"] = active
            tickets.append(ticket)
        except (TypeError, ValueError) as exc:
            rejected.append({"index": index, "reason": str(exc)})
    return {
        "status": "analyzed" if tickets else ("rejected" if rejected else "empty"),
        "read_only": True,
        "tickets_received": len(records),
        "tickets_analyzed": len(tickets),
        "tickets_rejected": len(rejected),
        "open_tickets": sum(t["status"] not in {"resolved", "closed"} for t in tickets),
        "urgent_tickets": [t["ticket_id"] for t in tickets if t["priority"] == "urgent" and t["status"] not in {"resolved", "closed"}],
        "stale_tickets": [t["ticket_id"] for t in tickets if t["stale_update_detected"]],
        "tickets": tickets,
        "rejections": rejected,
        "limitations": [
            "Les résumés doivent être anonymisés avant transmission ; les conversations brutes et données personnelles sont refusées.",
            "Les réponses sont des brouillons génériques à vérifier par un humain, jamais envoyés automatiquement.",
            "Aucune identité, commande, transaction, promesse commerciale ou politique de remboursement n'est vérifiée.",
        ],
    }
