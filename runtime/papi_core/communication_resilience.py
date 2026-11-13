"""Résilience des notifications : idempotence, quotas et audit fail-closed."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from .communication_channels import OwnerEmailNotification


class NotificationGuardError(RuntimeError):
    """Le garde-fou ne peut garantir une livraison sûre."""


class NotificationAlreadyProcessed(NotificationGuardError):
    """La clé d'idempotence a déjà été consommée."""


class NotificationRateLimited(NotificationGuardError):
    """Le quota de notification est atteint."""


@dataclass(frozen=True)
class NotificationAuditEvent:
    notification_id: str
    agent_id: str
    priority: str
    reason_code: str
    outcome: str
    occurred_at: str
    correlation_id: str
    idempotency_key: str


class IdempotencyStore(Protocol):
    async def claim(self, key: str, expires_at: str) -> bool:
        """Réserve atomiquement une clé unique jusqu'à son expiration."""


class NotificationRateStore(Protocol):
    async def consume(self, agent_id: str, category: str, limit: int, window_seconds: int) -> bool:
        """Consomme atomiquement un quota par agent et catégorie."""


class NotificationAuditStore(Protocol):
    async def append(self, event: NotificationAuditEvent) -> None:
        """Ajoute un événement d'audit sans contenu sensible."""


@dataclass(frozen=True)
class NotificationLimits:
    per_agent_per_hour: int = 12
    per_category_per_hour: int = 6
    idempotency_ttl_seconds: int = 86400

    def __post_init__(self):
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 1
               for value in (self.per_agent_per_hour, self.per_category_per_hour,
                             self.idempotency_ttl_seconds)):
            raise ValueError("Limites de notification invalides.")


class NotificationGuard:
    """Garde-fou à stockage injecté ; l'absence de stockage bloque l'envoi."""

    def __init__(self, *, idempotency: IdempotencyStore,
                 rate_store: NotificationRateStore, audit: NotificationAuditStore,
                 limits: NotificationLimits = NotificationLimits()):
        if idempotency is None or rate_store is None or audit is None:
            raise ValueError("Les stockages d'idempotence, quota et audit sont obligatoires.")
        self._idempotency = idempotency
        self._rate_store = rate_store
        self._audit = audit
        self._limits = limits

    async def authorize(self, notification: OwnerEmailNotification) -> None:
        now = datetime.now(timezone.utc)
        expires = now.timestamp() + self._limits.idempotency_ttl_seconds
        expires_at = datetime.fromtimestamp(expires, timezone.utc).isoformat()
        try:
            claimed = await self._idempotency.claim(notification.idempotency_key, expires_at)
            if not claimed:
                raise NotificationAlreadyProcessed("Notification déjà traitée.")
            allowed_agent = await self._rate_store.consume(
                notification.agent_id, "all", self._limits.per_agent_per_hour, 3600)
            allowed_category = await self._rate_store.consume(
                notification.agent_id, notification.reason_code,
                self._limits.per_category_per_hour, 3600)
            if not allowed_agent or not allowed_category:
                raise NotificationRateLimited("Quota de notification atteint.")
        except NotificationGuardError:
            raise
        except Exception as exc:
            raise NotificationGuardError("Stockage de contrôle indisponible ; envoi bloqué.") from exc

    async def record(self, notification: OwnerEmailNotification, outcome: str) -> None:
        event = NotificationAuditEvent(
            notification_id=notification.notification_id,
            agent_id=notification.agent_id,
            priority=notification.priority,
            reason_code=notification.reason_code,
            outcome=outcome,
            occurred_at=datetime.now(timezone.utc).isoformat(),
            correlation_id=notification.correlation_id,
            idempotency_key=notification.idempotency_key,
        )
        try:
            await self._audit.append(event)
        except Exception as exc:
            raise NotificationGuardError("Journal d'audit indisponible.") from exc
