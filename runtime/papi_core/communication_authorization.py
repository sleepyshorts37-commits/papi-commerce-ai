"""Autorisation et routage strict des canaux de communication PAPI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .agent_identity_card import IdentityCardError, validate_identity_card
from .communication_resilience import NotificationGuard\nfrom .communication_channels import (
    OwnerEmailNotification, OwnerEmailSender, DeliveryReceipt,
    InvalidChannelPayloadError, validate_owner_notification,
)


class CommunicationAuthorizationError(PermissionError):
    """Identité, permission ou destination non autorisée."""


@dataclass(frozen=True)
class OwnerDestination:
    """Configuration de destination chargée côté serveur, jamais par un agent."""
    email: str
    verified: bool
    allowlisted: bool
    notifications_enabled: bool


class OwnerCommunicationRouter:
    """Route uniquement vers l'adresse propriétaire vérifiée et autorisée.

    Les profils et cartes sont fournis par une couche de confiance (registre).
    Aucun champ d'adresse arbitraire n'est accepté dans une notification.
    """

    def __init__(
        self,
        *,
        agent_profiles: Mapping[str, dict],
        identity_cards: Mapping[str, dict],
        owner_destination: OwnerDestination,
        email_sender: OwnerEmailSender,
    ) -> None:
        self._profiles = agent_profiles
        self._cards = identity_cards
        self._destination = owner_destination
        self._sender = email_sender\n        self._notification_guard = notification_guard

    def _authorize_agent(self, agent_id: str, permission: str) -> None:
        if not isinstance(agent_id, str) or not agent_id:
            raise CommunicationAuthorizationError("Identifiant agent absent.")
        profile = self._profiles.get(agent_id)
        card = self._cards.get(agent_id)
        if not isinstance(profile, dict) or not isinstance(card, dict):
            raise CommunicationAuthorizationError("Agent absent du registre de confiance.")
        try:
            validate_identity_card(card)
        except IdentityCardError as exc:
            raise CommunicationAuthorizationError("Carte d'identité invalide.") from exc
        if card.get("agent_id") != agent_id or profile.get("id") != agent_id:
            raise CommunicationAuthorizationError("Identité agent incohérente.")
        if profile.get("status") != "active" or card.get("status") != "active":
            raise CommunicationAuthorizationError("Agent non actif.")
        profile_permissions = profile.get("permissions")
        card_permissions = card.get("permissions")
        if not isinstance(profile_permissions, list) or not isinstance(card_permissions, list):
            raise CommunicationAuthorizationError("Permissions absentes.")
        # L'autorisation exige la concordance entre registre et carte d'identité.
        if set(profile_permissions) != set(card_permissions):
            raise CommunicationAuthorizationError("Permissions divergentes entre registre et carte.")
        if permission not in profile_permissions:
            raise CommunicationAuthorizationError("Permission absente pour cette action.")

    def authorize_voice_session(self, agent_id: str) -> None:
        """Autorise un agent à participer à une session vocale explicitement ouverte."""
        self._authorize_agent(agent_id, "voice_session")

    async def send_owner_notification(
        self, notification: OwnerEmailNotification
    ) -> DeliveryReceipt:
        validate_owner_notification(notification)
        self._authorize_agent(notification.agent_id, "notify_owner_email")
        destination = self._destination
        if not destination.verified or not destination.allowlisted:
            raise CommunicationAuthorizationError("Adresse propriétaire non vérifiée ou non autorisée.")
        if not destination.notifications_enabled:
            raise CommunicationAuthorizationError("Notifications propriétaire désactivées.")
        if (
            not isinstance(destination.email, str)
            or destination.email.count("@") != 1
            or any(char.isspace() for char in destination.email)
            or len(destination.email) > 254
            or "." not in destination.email.rsplit("@", 1)[-1]
            or destination.email.startswith("@")
            or destination.email.endswith("@")
        ):
            raise CommunicationAuthorizationError("Configuration de destination invalide.")
        # L'adresse reste dans la configuration du sender injecté ; l'agent ne la fournit jamais.
        try:
            return await self._sender.send_owner_notification(notification)
        except Exception:
            # Échec fermé : aucun autre destinataire ni fournisseur de secours implicite.
            raise
