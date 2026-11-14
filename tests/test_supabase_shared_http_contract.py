"""Contrats HTTP réels de l'adaptateur Supabase sans réseau ni secret hébergé.

Ces tests traversent SupabaseStore._request et SharedCollaborationStore. Le transport
est remplacé à la frontière urllib afin de vérifier URL, en-têtes, payload et erreurs.
"""
from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from papi_core.principal import _issue_authenticated_agent_principal
from papi_core.shared_collaboration import SharedCollaborationStore
from papi_core.storage import StoreError, SupabaseStore


class FakeHTTPResponse:
    def __init__(self, payload: object, status: int = 200):
        self.status = status
        self._body = json.dumps(payload).encode("utf-8") if payload is not None else b""

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self._body


class SupabaseSharedHTTPContractTests(unittest.TestCase):
    def setUp(self):
        self.store = SupabaseStore(
            url="https://papi-test.supabase.co",
            key="test-only-service-role-secret",
            timeout=3,
        )

    @patch("papi_core.storage.urlopen")
    def test_shared_memory_write_uses_server_auth_and_idempotent_post(self, mocked_urlopen):
        row = {
            "event_id": "event-1", "memory_id": "memory-1",
            "actor": "astou", "category": "fact", "title": "Règle",
            "content": "Contrôle validé.", "source_type": "test",
            "source_id": "http-contract-1", "confidence": 0.8,
            "scope": "shared", "tags": [], "sensitivity": "normal",
            "idempotency_key": "http-memory-key-001",
        }
        mocked_urlopen.return_value = FakeHTTPResponse([row])
        adapter = SharedCollaborationStore(store=self.store)
        result = adapter.remember(
            principal=_issue_authenticated_agent_principal("astou"),
            category="fact", title="Règle", content="Contrôle validé.",
            source_type="test", source_id="http-contract-1",
            idempotency_key="http-memory-key-001",
        )

        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://papi-test.supabase.co/rest/v1/papi_memory_events?on_conflict=idempotency_key")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Apikey"), "test-only-service-role-secret")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-only-service-role-secret")
        self.assertEqual(request.get_header("Prefer"), "resolution=ignore-duplicates,return=representation")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["actor"], "astou")
        self.assertEqual(payload["idempotency_key"], "http-memory-key-001")
        self.assertEqual(result["event_id"], "event-1")

    @patch("papi_core.storage.urlopen")
    def test_chat_read_keeps_recipient_filter_in_server_query(self, mocked_urlopen):
        mocked_urlopen.return_value = FakeHTTPResponse([])
        adapter = SharedCollaborationStore(store=self.store)
        adapter.read_messages(principal=_issue_authenticated_agent_principal("astou"))

        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertIn("recipient.eq.all", request.full_url)
        self.assertIn("recipient.eq.astou", request.full_url)
        self.assertIn("order=sent_at.desc,message_id.desc", request.full_url)
        self.assertIsNone(request.data)

    @patch("papi_core.storage.urlopen")
    def test_http_error_does_not_expose_response_body_or_credentials(self, mocked_urlopen):
        mocked_urlopen.side_effect = HTTPError(
            "https://papi-test.supabase.co/rest/v1/papi_chat_messages",
            403, "Forbidden", {}, io.BytesIO(b"private database detail"),
        )
        with self.assertRaises(StoreError) as raised:
            self.store._request("GET", "papi_chat_messages?select=message_id")
        message = str(raised.exception)
        self.assertIn("HTTP 403", message)
        self.assertNotIn("private database detail", message)
        self.assertNotIn("test-only-service-role-secret", message)

    @patch("papi_core.storage.urlopen")
    def test_transport_never_logs_or_returns_server_key(self, mocked_urlopen):
        mocked_urlopen.return_value = FakeHTTPResponse([])
        self.store._request("GET", "papi_chat_messages?select=message_id")
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-only-service-role-secret")
        self.assertNotIn("test-only-service-role-secret", request.full_url)


if __name__ == "__main__":
    unittest.main()
