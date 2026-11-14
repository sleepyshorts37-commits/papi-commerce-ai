import unittest

from papi_core.storage import StoreError, SupabaseStore
from papi_core.worker_store import (
    SupabaseWorkerStore, WorkerStoreError, build_worker_sync_event,
)


class FakeWorkerStore:
    def __init__(self):
        self.sync_calls = []
        self.read_calls = []

    def sync_worker_event(self, event, *, expected_version):
        self.sync_calls.append((event, expected_version))
        return {"duplicate": False, "event_id": event["event_id"], "record_version": expected_version + 1}

    def list_worker_records(self, domain, *, limit=500):
        self.read_calls.append((domain, limit))
        return {
            "platform_candidate": [{"platform_id": "P-1", "status": "needs_human_review"}],
            "human_handoff": [{"handoff_id": "H-1", "status": "awaiting_user"}],
            "profitability_result": [{"offer_id": "O-1", "status": "viable_for_human_review"}],
        }[domain]


class StubSupabaseStore(SupabaseStore):
    def __init__(self, responses):
        super().__init__("https://example.supabase.co", "server-test-key")
        self.responses = list(responses)
        self.calls = []

    def _request(self, method, path, payload=None, prefer=None):
        self.calls.append((method, path, payload, prefer))
        return self.responses.pop(0)


class WorkerStoreAdapterTests(unittest.TestCase):
    def _event(self):
        return build_worker_sync_event(
            domain="human_handoff",
            record_id="H-1",
            source_event_id="source-1",
            event_type="handoff_created",
            actor="agent-astou",
            occurred_at="2026-11-14T08:15:00Z",
            payload={"status": "awaiting_user"},
        )

    def test_sync_event_delegates_to_injected_store_with_version(self):
        fake = FakeWorkerStore()
        adapter = SupabaseWorkerStore(fake)
        event = self._event()
        result = adapter.sync_event(event, expected_version=0)
        self.assertFalse(result["duplicate"])
        self.assertEqual(fake.sync_calls, [(event, 0)])

    def test_tampered_idempotency_key_is_rejected_before_network(self):
        fake = FakeWorkerStore()
        adapter = SupabaseWorkerStore(fake)
        event = self._event()
        event["idempotency_key"] = "0" * 64
        with self.assertRaises(WorkerStoreError):
            adapter.sync_event(event, expected_version=0)
        self.assertEqual(fake.sync_calls, [])

    def test_load_worker_inputs_reads_only_three_allowlisted_domains(self):
        fake = FakeWorkerStore()
        result = SupabaseWorkerStore(fake).load_worker_inputs(limit_per_domain=25)
        self.assertEqual(result["platform_candidates"][0]["platform_id"], "P-1")
        self.assertEqual(result["handoffs"][0]["handoff_id"], "H-1")
        self.assertEqual(result["profitability_results"][0]["offer_id"], "O-1")
        self.assertEqual(fake.read_calls, [
            ("platform_candidate", 25),
            ("human_handoff", 25),
            ("profitability_result", 25),
        ])

    def test_invalid_domain_limit_or_store_is_rejected(self):
        with self.assertRaises(WorkerStoreError):
            SupabaseWorkerStore(object())
        adapter = SupabaseWorkerStore(FakeWorkerStore())
        with self.assertRaises(WorkerStoreError):
            adapter.load_worker_inputs(limit_per_domain=0)

    def test_supabase_store_calls_atomic_rpc_with_server_store(self):
        stub = StubSupabaseStore([{"duplicate": False, "event_id": "WEVT", "record_version": 1}])
        result = stub.sync_worker_event(self._event(), expected_version=0)
        self.assertEqual(result["record_version"], 1)
        method, path, payload, _ = stub.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(path, "rpc/papi_sync_worker_record")
        self.assertEqual(payload["p_expected_version"], 0)
        self.assertEqual(payload["p_domain"], "human_handoff")

    def test_supabase_store_reads_domain_and_maps_record_identifier(self):
        stub = StubSupabaseStore([[
            {"domain": "human_handoff", "record_id": "H-9",
             "payload": {"status": "awaiting_user"}, "version": 1}
        ]])
        records = stub.list_worker_records("human_handoff", limit=20)
        self.assertEqual(records, [{"status": "awaiting_user", "handoff_id": "H-9"}])
        self.assertIn("domain=eq.human_handoff", stub.calls[0][1])

    def test_supabase_store_rejects_sensitive_fields_and_invalid_domains(self):
        stub = StubSupabaseStore([[
            {"domain": "human_handoff", "record_id": "H-9",
             "payload": {"access_token": "never-store"}, "version": 1}
        ]])
        with self.assertRaises(WorkerStoreError):
            stub.list_worker_records("human_handoff")
        with self.assertRaises(StoreError):
            StubSupabaseStore([]).list_worker_records("unknown")


if __name__ == "__main__":
    unittest.main()
