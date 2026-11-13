import unittest
from papi_core.communication_resilience import (
    NotificationAlreadyProcessed, NotificationGuard, NotificationGuardError,
    NotificationLimits, NotificationRateLimited,
)
from papi_core.communication_channels import OwnerEmailNotification


class FakeIdempotency:
    def __init__(self): self.keys = set()
    async def claim(self, key, expires_at):
        if key in self.keys: return False
        self.keys.add(key); return True


class FakeRateStore:
    def __init__(self): self.counts = {}
    async def consume(self, agent_id, category, limit, window_seconds):
        key=(agent_id, category); self.counts[key]=self.counts.get(key,0)+1
        return self.counts[key] <= limit


class FakeAudit:
    def __init__(self): self.events=[]
    async def append(self, event): self.events.append(event)


class FailingStore:
    async def claim(self, key, expires_at): raise OSError("unavailable")


class NotificationResilienceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.idem=FakeIdempotency(); self.rates=FakeRateStore(); self.audit=FakeAudit()
        self.guard=NotificationGuard(idempotency=self.idem,rate_store=self.rates,audit=self.audit,
            limits=NotificationLimits(per_agent_per_hour=2,per_category_per_hour=1))
        self.note=OwnerEmailNotification(
            notification_id="n1",agent_id="astou",priority="P1",reason_code="incident",
            subject="Incident",body="Alerte",correlation_id="c1",idempotency_key="i1",
            created_at="2026-11-13T12:00:00Z")

    async def test_idempotency_blocks_duplicate(self):
        await self.guard.authorize(self.note)
        with self.assertRaises(NotificationAlreadyProcessed):
            await self.guard.authorize(self.note)

    async def test_category_quota_blocks_burst(self):
        await self.guard.authorize(self.note)
        second=OwnerEmailNotification(**{**self.note.__dict__,"notification_id":"n2","idempotency_key":"i2"})
        with self.assertRaises(NotificationRateLimited):
            await self.guard.authorize(second)

    async def test_audit_records_metadata_only(self):
        await self.guard.record(self.note,"accepted")
        self.assertEqual(len(self.audit.events),1)
        self.assertFalse(hasattr(self.audit.events[0],"body"))

    async def test_storage_failure_fails_closed(self):
        guard=NotificationGuard(idempotency=FailingStore(),rate_store=self.rates,audit=self.audit)
        with self.assertRaises(NotificationGuardError):
            await guard.authorize(self.note)

    def test_invalid_limits_rejected(self):
        with self.assertRaises(ValueError):
            NotificationLimits(per_agent_per_hour=0)


if __name__ == "__main__": unittest.main()
