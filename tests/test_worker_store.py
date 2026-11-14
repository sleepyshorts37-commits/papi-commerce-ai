import unittest

from papi_core.worker_store import WorkerStoreError, build_worker_sync_event


class WorkerStoreEventTests(unittest.TestCase):
    def _event(self, **overrides):
        values = {
            "domain": "human_handoff",
            "record_id": "HANDOFF-001",
            "source_event_id": "source-event-001",
            "event_type": "handoff_created",
            "actor": "agent-astou",
            "occurred_at": "2026-11-14T08:15:00Z",
            "payload": {"status": "awaiting_user", "attempt": 1},
        }
        values.update(overrides)
        return build_worker_sync_event(**values)

    def test_retries_generate_identical_event_and_idempotency_ids(self):
        first = self._event()
        retry = self._event()
        self.assertEqual(first["event_id"], retry["event_id"])
        self.assertEqual(first["idempotency_key"], retry["idempotency_key"])
        self.assertEqual(len(first["idempotency_key"]), 64)
        self.assertFalse(first["persistence_performed"])
        self.assertFalse(first["network_access_performed"])

    def test_different_source_events_have_different_idempotency_keys(self):
        first = self._event(source_event_id="source-event-001")
        second = self._event(source_event_id="source-event-002")
        self.assertNotEqual(first["idempotency_key"], second["idempotency_key"])

    def test_domain_is_allowlisted(self):
        with self.assertRaises(WorkerStoreError):
            self._event(domain="arbitrary_table")

    def test_sensitive_payload_fields_are_rejected_recursively(self):
        with self.assertRaises(WorkerStoreError):
            self._event(payload={"profile": {"access_token": "do-not-store"}})
        with self.assertRaises(WorkerStoreError):
            self._event(payload={"password": "do-not-store"})

    def test_payload_must_be_json_safe_object(self):
        with self.assertRaises(WorkerStoreError):
            self._event(payload=["not", "an", "object"])
        with self.assertRaises(WorkerStoreError):
            self._event(payload={"amount": float("nan")})

    def test_timestamp_must_be_valid_and_timezone_aware(self):
        with self.assertRaises(WorkerStoreError):
            self._event(occurred_at="2026-11-14T08:15:00")
        with self.assertRaises(WorkerStoreError):
            self._event(occurred_at="not-a-date")

    def test_supported_domains_cover_worker_modules(self):
        for domain in ("platform_candidate", "human_handoff", "profitability_result"):
            self.assertEqual(self._event(domain=domain)["domain"], domain)


if __name__ == "__main__":
    unittest.main()
