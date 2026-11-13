import unittest
from unittest.mock import AsyncMock

from papi_core.agent_identity_card import create_identity_card
from papi_core.communication_authorization import (
    CommunicationAuthorizationError, OwnerCommunicationRouter, OwnerDestination,
)
from papi_core.communication_channels import DeliveryReceipt, OwnerEmailNotification


class FakeNotificationGuard:
    async def authorize(self, notification):
        return None
    async def record(self, notification, outcome):
        return None


class OwnerCommunicationAuthorizationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.profile = {
            "id": "astou", "name": "Astou", "role": "Direction",
            "department": "Direction", "status": "active",
            "permissions": ["notify_owner_email", "voice_session"],
            "autonomy_level": "bounded",
        }
        self.card = create_identity_card(self.profile, "2026-11-13", "president")
        self.sender = AsyncMock()
        self.sender.send_owner_notification.return_value = DeliveryReceipt("provider-1", "2026-11-13T12:00:00Z")
        self.destination = OwnerDestination("owner@example.org", True, True, True)
        self.router = OwnerCommunicationRouter(
            agent_profiles={"astou": self.profile},
            identity_cards={"astou": self.card},
            owner_destination=self.destination,
            email_sender=self.sender,
        )
        self.notification = OwnerEmailNotification(
            notification_id="n-1", agent_id="astou", priority="P1",
            reason_code="decision", subject="Validation requise",
            body="Une validation est nécessaire.", correlation_id="c-1",
            idempotency_key="i-1", created_at="2026-11-13T12:00:00Z",
        )

    async def test_sends_only_after_identity_permission_and_destination_checks(self):
        receipt = await self.router.send_owner_notification(self.notification)
        self.assertEqual(receipt.provider_message_id, "provider-1")
        self.sender.send_owner_notification.assert_awaited_once_with(self.notification)

    async def test_rejects_inactive_agent(self):
        self.profile["status"] = "suspended"
        with self.assertRaises(CommunicationAuthorizationError):
            await self.router.send_owner_notification(self.notification)
        self.sender.send_owner_notification.assert_not_awaited()

    async def test_rejects_missing_permission(self):
        self.profile["permissions"] = ["voice_session"]
        self.card["permissions"] = ["voice_session"]
        with self.assertRaises(CommunicationAuthorizationError):
            await self.router.send_owner_notification(self.notification)
        self.sender.send_owner_notification.assert_not_awaited()

    async def test_rejects_tampered_or_mismatched_identity(self):
        self.card["agent_id"] = "other"
        with self.assertRaises(CommunicationAuthorizationError):
            await self.router.send_owner_notification(self.notification)
        self.sender.send_owner_notification.assert_not_awaited()

    async def test_rejects_unverified_or_disabled_owner_destination(self):
        for destination in (
            OwnerDestination("owner@example.org", False, True, True),
            OwnerDestination("owner@example.org", True, False, True),
            OwnerDestination("owner@example.org", True, True, False),
        ):
            router = OwnerCommunicationRouter(
                agent_profiles={"astou": self.profile},
                identity_cards={"astou": self.card},
                owner_destination=destination, email_sender=self.sender,
            )
            with self.assertRaises(CommunicationAuthorizationError):
                await router.send_owner_notification(self.notification)
        self.sender.send_owner_notification.assert_not_awaited()

    async def test_rejects_invalid_owner_destination_configuration(self):
        router = OwnerCommunicationRouter(
            agent_profiles={"astou": self.profile},
            identity_cards={"astou": self.card},
            owner_destination=OwnerDestination("not-an-email", True, True, True),
            email_sender=self.sender,
        )
        with self.assertRaises(CommunicationAuthorizationError):
            await router.send_owner_notification(self.notification)
        self.sender.send_owner_notification.assert_not_awaited()

    async def test_voice_permission_is_separate(self):
        self.router.authorize_voice_session("astou")
        self.profile["permissions"] = ["notify_owner_email"]
        self.card["permissions"] = ["notify_owner_email"]
        with self.assertRaises(CommunicationAuthorizationError):
            self.router.authorize_voice_session("astou")


if __name__ == "__main__":
    unittest.main()
