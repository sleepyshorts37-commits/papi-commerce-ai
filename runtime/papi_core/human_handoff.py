"""Human handoff and safe resumption for PAPI AI WORKERS platform onboarding.

Pure state transitions only: no notification delivery, account creation,
credential collection, payment, or external platform action is performed.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

STATES = {"discovered", "awaiting_user", "user_confirmed", "resumed", "completed", "rejected"}
SENSITIVE_KEYS = {
    "password", "passwd", "otp", "one_time_code", "verification_code",
    "private_key", "secret_key", "seed_phrase", "recovery_phrase",
    "card_number", "cvv", "cvc", "access_token", "refresh_token",
}


class HumanHandoffError(ValueError):
    """Invalid handoff or unauthorized state transition."""


def _actor(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 160:
        raise HumanHandoffError(f"{field} est obligatoire.")
    return value.strip()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _reject_sensitive(value: Any, path: str = "payload") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().casefold().replace("-", "_")
            if normalized in SENSITIVE_KEYS:
                raise HumanHandoffError(f"Champ confidentiel interdit dans {path}.{key}.")
            _reject_sensitive(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_sensitive(child, f"{path}[{index}]")


def create_handoff(
    *,
    platform_id: str,
    platform_name: str,
    official_url: str,
    required_user_action: str,
    created_by_agent_id: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a paused onboarding handoff without collecting user credentials."""
    for field, value in (
        ("platform_id", platform_id), ("platform_name", platform_name),
        ("official_url", official_url), ("required_user_action", required_user_action),
        ("created_by_agent_id", created_by_agent_id),
    ):
        _actor(value, field)
    if not official_url.startswith("https://"):
        raise HumanHandoffError("Le lien officiel doit utiliser HTTPS.")
    safe_context = context or {}
    if not isinstance(safe_context, dict):
        raise HumanHandoffError("context doit être un objet.")
    _reject_sensitive(safe_context)
    handoff_id = f"HANDOFF-{uuid4().hex.upper()}"
    created_at = _now()
    return {
        "handoff_id": handoff_id,
        "platform_id": platform_id,
        "platform_name": platform_name,
        "official_url": official_url,
        "required_user_action": required_user_action,
        "created_by_agent_id": created_by_agent_id,
        "context": deepcopy(safe_context),
        "status": "awaiting_user",
        "created_at": created_at,
        "updated_at": created_at,
        "user_confirmation": None,
        "resumed_by_agent_id": None,
        "events": [{
            "event_id": f"EVT-{uuid4().hex.upper()}",
            "type": "human_action_requested",
            "actor": created_by_agent_id,
            "at": created_at,
        }],
        "external_actions_performed": False,
    }


def confirm_user_action(
    handoff: dict[str, Any], *, user_actor: str, confirmation: str,
) -> dict[str, Any]:
    """Record the user's explicit confirmation; does not verify the external account."""
    if not isinstance(handoff, dict) or handoff.get("status") != "awaiting_user":
        raise HumanHandoffError("Cette demande n'attend pas une confirmation utilisateur.")
    actor = _actor(user_actor, "user_actor")
    statement = _actor(confirmation, "confirmation")
    _reject_sensitive({"confirmation": statement})
    updated = deepcopy(handoff)
    updated["status"] = "user_confirmed"
    updated["user_confirmation"] = {
        "actor": actor,
        "statement": statement,
        "at": _now(),
        "verification_method": "user_attestation",
    }
    updated["updated_at"] = updated["user_confirmation"]["at"]
    updated["events"].append({
        "event_id": f"EVT-{uuid4().hex.upper()}",
        "type": "user_action_confirmed",
        "actor": actor,
        "at": updated["updated_at"],
    })
    return updated


def resume_after_user_confirmation(
    handoff: dict[str, Any], *, agent_id: str,
) -> dict[str, Any]:
    """Allow workflow resumption only after explicit user attestation."""
    if not isinstance(handoff, dict) or handoff.get("status") != "user_confirmed":
        raise HumanHandoffError("La confirmation explicite de l'utilisateur est requise.")
    actor = _actor(agent_id, "agent_id")
    updated = deepcopy(handoff)
    updated["status"] = "resumed"
    updated["resumed_by_agent_id"] = actor
    updated["updated_at"] = _now()
    updated["events"].append({
        "event_id": f"EVT-{uuid4().hex.upper()}",
        "type": "workflow_resumed",
        "actor": actor,
        "at": updated["updated_at"],
    })
    return updated


def close_handoff(
    handoff: dict[str, Any], *, actor: str, outcome: str,
) -> dict[str, Any]:
    """Close a resumed handoff as completed or rejected with an audit reason."""
    if not isinstance(handoff, dict) or handoff.get("status") != "resumed":
        raise HumanHandoffError("Seule une demande reprise peut être clôturée.")
    if outcome not in {"completed", "rejected"}:
        raise HumanHandoffError("Résultat de clôture invalide.")
    who = _actor(actor, "actor")
    reason = _actor(outcome, "outcome")
    updated = deepcopy(handoff)
    updated["status"] = outcome
    updated["updated_at"] = _now()
    updated["events"].append({
        "event_id": f"EVT-{uuid4().hex.upper()}",
        "type": f"handoff_{reason}",
        "actor": who,
        "at": updated["updated_at"],
    })
    return updated
