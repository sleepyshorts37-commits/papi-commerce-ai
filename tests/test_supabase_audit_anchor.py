import hashlib
import json
import unittest
from unittest.mock import Mock

from runtime.papi_core.storage import StoreError, SupabaseStore
from runtime.papi_core.supabase_audit_anchor import SupabaseCheckpointStore


class SupabaseCheckpointStoreTests(unittest.TestCase):
    def setUp(self):
        client = object.__new__(SupabaseStore)
        client.request = Mock()
        self.client = client
        self.adapter = SupabaseCheckpointStore(client)

    def test_public_request_interface_delegates_without_exposing_credentials(self):
        client = object.__new__(SupabaseStore)
        client._request = Mock(return_value=[{"ok": True}])
        result = client.request("GET", "health")
        self.assertEqual(result, [{"ok": True}])
        client._request.assert_called_once_with("GET", "health", None, None)

    def record(self):
        return {
            "schema_version": 1,
            "journal_id": "journal-01",
            "checkpoint": {
                "schema_version": 1,
                "sequence": 1,
                "head_hash": "a" * 64,
            },
            "previous_record_digest": None,
            "key_id": "test-key",
            "signature": "test-signature",
        }

    def test_get_latest_returns_none_or_digest(self):
        self.client.request.return_value = []
        self.assertIsNone(self.adapter.get_latest("journal-01"))
        self.client.request.return_value = [{"latest_record_digest": "b" * 64}]
        self.assertEqual(self.adapter.get_latest("journal-01"), "b" * 64)

    def test_get_record_returns_exact_utf8_bytes(self):
        canonical = json.dumps(self.record(), sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        self.client.request.return_value = [{"canonical_record": canonical}]
        self.assertEqual(self.adapter.get_record(digest), canonical.encode("utf-8"))

    def test_put_record_checks_digest_and_read_after_write(self):
        canonical = json.dumps(self.record(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        digest = hashlib.sha256(canonical).hexdigest()

        def request(method, path, payload=None, prefer=None):
            if method == "POST":
                self.assertIn("resolution=ignore-duplicates", prefer)
                return None
            return [{"canonical_record": canonical.decode("utf-8")}]

        self.client.request.side_effect = request
        self.adapter.put_record(digest, canonical)
        with self.assertRaises(StoreError):
            self.adapter.put_record("0" * 64, canonical)

    def test_compare_and_swap_uses_atomic_rpc(self):
        canonical = json.dumps(self.record(), sort_keys=True, separators=(",", ":"))
        self.client.request.side_effect = [
            [{"canonical_record": canonical}],
            True,
        ]
        self.assertTrue(self.adapter.compare_and_swap_latest(
            "journal-01", None, hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        ))
        self.assertEqual(
            self.client.request.call_args_list[1].args[1],
            "rpc/papi_advance_audit_anchor",
        )

    def test_compare_and_swap_rejects_record_for_another_journal(self):
        record = self.record()
        record["journal_id"] = "other-journal"
        canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        self.client.request.return_value = [{"canonical_record": canonical}]
        with self.assertRaises(StoreError):
            self.adapter.compare_and_swap_latest("journal-01", None, digest)

    def test_non_boolean_rpc_result_fails_closed(self):
        canonical = json.dumps(self.record(), sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        self.client.request.side_effect = [
            [{"canonical_record": canonical}],
            {"success": True},
        ]
        with self.assertRaises(StoreError):
            self.adapter.compare_and_swap_latest("journal-01", None, digest)


if __name__ == "__main__":
    unittest.main()
