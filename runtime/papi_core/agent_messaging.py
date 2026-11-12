"""Messagerie interne documentaire : candidats et projection d'événements, sans livraison."""
from __future__ import annotations

import re
from typing import Any

from .audit import validate_event
from .identity_security import IdentitySecurityError, validate_identity_registry

MESSAGE_TYPES = {"task.proposal", "task.assignment", "task.update", "report", "alert", "question", "answer"}
PRIORITIES = {"low", "normal", "high", "critical"}
MESSAGE_PERMISSION = "send_internal_messages"
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,119}$")
_EMAIL = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d .()/-]{7,}\d)(?!\w)")


class AgentMessagingError(ValueError):
    """Enveloppe de message invalide ou non autorisée."""


def _identity_maps(identity_document: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    validate_identity_registry(identity_document)
    identities = {item["agent_id"]: item for item in identity_document["identities"]}
    return identities, identity_document


def build_message_candidate(
    *, sender_id: str, recipient_id: str, message_type: str, subject: str,
    body: str, priority: str, created_at: str, message_id: str,
    identity_document: dict[str, Any], agents: dict[str, dict[str, Any]],
    task_id: str | None = None,
) -> dict[str, Any]:
    """Prépare un brouillon uniquement si l'identité émettrice est explicitement habilitée."""
    identities, _ = _identity_maps(identity_document)
    sender = identities.get(sender_id)
    recipient = identities.get(recipient_id)
    registry_sender = agents.get(sender_id)
    if sender is None or recipient is None or registry_sender is None or recipient_id not in agents:
        raise AgentMessagingError("Émetteur ou destinataire absent des registres.")
    if sender.get("status") not in {"active", "deployed"} or registry_sender.get("status") not in {"active", "deployed"}:
        raise AgentMessagingError("Émetteur non actif : création du message refusée.")
    if sender.get("profile_state") != "complete":
        raise AgentMessagingError("Profil émetteur incomplet.")
    if MESSAGE_PERMISSION in sender.get("prohibited_actions", []) or MESSAGE_PERMISSION not in sender.get("permissions", []):
        raise AgentMessagingError("Permission send_internal_messages absente ou interdite.")
    if not isinstance(message_id, str) or not _ID.fullmatch(message_id):
        raise AgentMessagingError("message_id invalide.")
    if message_type not in MESSAGE_TYPES or priority not in PRIORITIES:
        raise AgentMessagingError("Type ou priorité de message invalide.")
    if not isinstance(subject, str) or not subject.strip() or len(subject) > 160:
        raise AgentMessagingError("Sujet invalide (1 à 160 caractères).")
    if not isinstance(body, str) or not body.strip() or len(body) > 500:
        raise AgentMessagingError("Corps invalide (1 à 500 caractères).")
    if _EMAIL.search(body) or _PHONE.search(body):
        raise AgentMessagingError("Le corps semble contenir une coordonnée personnelle ; contenu refusé.")
    if task_id is not None and (not isinstance(task_id, str) or not _ID.fullmatch(task_id)):
        raise AgentMessagingError("task_id invalide.")
    details = {
        "message_id": message_id, "recipient_id": recipient_id,
        "message_type": message_type, "subject": subject.strip(),
        "body": body.strip(), "priority": priority, "task_id": task_id,
    }
    event = {
        "event_id": f"MSG-EVENT-{message_id}", "occurred_at": created_at,
        "actor": sender_id, "action": "agent.message.candidate",
        "entity_type": "agent_message", "entity_id": message_id,
        "details": details,
    }
    try:
        validate_event(event)
    except ValueError as exc:
        raise AgentMessagingError(str(exc)) from exc
    return {
        "status": "draft_candidate", "message": {
            "message_id": message_id, "sender_id": sender_id,
            "recipient_id": recipient_id, "message_type": message_type,
            "subject": subject.strip(), "body": body.strip(),
            "priority": priority, "created_at": created_at, "task_id": task_id,
        },
        "permission_checked": MESSAGE_PERMISSION,
        "runtime_identity_authenticated": False,
        "owner_approval_checked": False,
        "persisted": False, "delivered": False, "task_assigned": False,
        "read_only": True,
    }


def build_message_center(events: list[dict[str, Any]], identity_document: dict[str, Any]) -> dict[str, Any]:
    """Projette uniquement les événements agent.message.created explicitement journalisés."""
    identities, _ = _identity_maps(identity_document)
    seen: set[str] = set()
    messages: list[dict[str, Any]] = []
    rejected = 0
    for event in events:
        if not isinstance(event, dict) or event.get("action") != "agent.message.created" or event.get("entity_type") != "agent_message":
            continue
        try:
            validate_event(event)
            details = event["details"]
            required = {"message_id", "recipient_id", "message_type", "subject", "body", "priority", "task_id"}
            if set(details) != required:
                raise AgentMessagingError("Schéma de message journalisé invalide.")
            message_id, sender_id, recipient_id = details["message_id"], event["actor"], details["recipient_id"]
            if message_id in seen or not isinstance(message_id, str):
                raise AgentMessagingError("Identifiant de message dupliqué ou invalide.")
            if sender_id not in identities or recipient_id not in identities:
                raise AgentMessagingError("Émetteur ou destinataire inconnu.")
            if identities[sender_id].get("status") not in {"active", "deployed"}:
                raise AgentMessagingError("Émetteur non actif.")
            if MESSAGE_PERMISSION not in identities[sender_id].get("permissions", []):
                raise AgentMessagingError("Permission d'envoi absente.")
            if details["message_type"] not in MESSAGE_TYPES or details["priority"] not in PRIORITIES:
                raise AgentMessagingError("Type ou priorité invalide.")
            if not isinstance(details["subject"], str) or len(details["subject"]) > 160:
                raise AgentMessagingError("Sujet invalide.")
            if not isinstance(details["body"], str) or not 1 <= len(details["body"]) <= 500:
                raise AgentMessagingError("Corps invalide.")
            seen.add(message_id)
            messages.append({
                "message_id": message_id, "sender_id": sender_id,
                "recipient_id": recipient_id, **details,
                "created_at": event["occurred_at"], "status": "recorded_event",
            })
        except (ValueError, KeyError, TypeError):
            rejected += 1
    messages.sort(key=lambda item: (item["created_at"], item["message_id"]))
    return {
        "status": "available" if messages else "no_recorded_messages",
        "messages": messages, "message_count": len(messages),
        "rejected_events": rejected, "source": "explicit_append_only_audit_events",
        "delivery_enabled": False, "read_only": True,
    }
