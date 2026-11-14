"""Run the production collaboration adapter against the disposable local PostgREST stack."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import time
import unittest
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runtime"))

from papi_core.principal import _issue_authenticated_agent_principal
from papi_core.shared_collaboration import SharedCollaborationStore


BASE_URL = os.environ.get("PAPI_LOCAL_REST_URL", "http://127.0.0.1:55433").rstrip("/")
JWT_SECRET = os.environ.get(
    "PAPI_LOCAL_JWT_SECRET",
    "papi_local_only_jwt_secret_change_before_any_nonlocal_use",
)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _token() -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64(json.dumps({
        "role": "service_role", "iss": "papi-local-adapter-test",
        "iat": int(time.time()), "exp": int(time.time()) + 300,
    }).encode())
    message = f"{header}.{payload}".encode()
    signature = hmac.new(JWT_SECRET.encode(), message, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64(signature)}"


class LocalPostgRESTStore:
    """Minimal local transport implementing the same _request contract as SupabaseStore."""

    def __init__(self) -> None:
        if not (BASE_URL.startswith("http://127.0.0.1:") or BASE_URL.startswith("http://localhost:")):
            raise RuntimeError("Refusing non-loopback REST URL; this test is local-only.")
        if len(JWT_SECRET) < 32:
            raise RuntimeError("Local JWT secret must contain at least 32 characters.")

    def _request(self, method, path, payload=None, prefer=None):
        headers = {
            "Authorization": f"Bearer {_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(f"{BASE_URL}/" + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError:
            raise


class LiveCollaborationAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = "integration_" + uuid.uuid4().hex[:12]
        cls.principal = _issue_authenticated_agent_principal(cls.agent)
        cls.adapter = SharedCollaborationStore(store=LocalPostgRESTStore())

    def test_memory_idempotency_and_real_search(self):
        key = "memory-" + uuid.uuid4().hex
        first = self.adapter.remember(
            principal=self.principal, category="fact", title="Local adapter fact",
            content="PostgREST persists this memory.", source_type="integration",
            source_id="mission-22-day-4", idempotency_key=key,
        )
        second = self.adapter.remember(
            principal=self.principal, category="fact", title="Local adapter fact",
            content="PostgREST persists this memory.", source_type="integration",
            source_id="mission-22-day-4", idempotency_key=key,
        )
        self.assertEqual(first["event_id"], second["event_id"])
        results = self.adapter.search_memory(
            principal=self.principal, query="PostgREST persists", limit=10
        )
        self.assertTrue(any(item["memory_id"] == first["memory_id"] for item in results["items"]))

    def test_chat_idempotency_and_recipient_scoped_reads(self):
        key = "chat-" + uuid.uuid4().hex
        message = self.adapter.send_message(
            principal=self.principal, recipient=self.agent,
            subject="Local adapter chat", body="Only intended recipient can find this.",
            idempotency_key=key, message_type="info",
        )
        duplicate = self.adapter.send_message(
            principal=self.principal, recipient=self.agent,
            subject="Local adapter chat", body="Only intended recipient can find this.",
            idempotency_key=key, message_type="info",
        )
        self.assertEqual(message["message_id"], duplicate["message_id"])
        page = self.adapter.read_messages(principal=self.principal, limit=20)
        self.assertTrue(any(item["message_id"] == message["message_id"] for item in page["items"]))

    def test_chat_keyset_pagination(self):
        for index in range(3):
            self.adapter.send_message(
                principal=self.principal, recipient=self.agent,
                subject=f"Pagination {index}", body=f"Page record {index}",
                idempotency_key=f"page-{uuid.uuid4().hex}", message_type="info",
            )
        first = self.adapter.read_messages(principal=self.principal, limit=1)
        self.assertEqual(len(first["items"]), 1)
        self.assertIsNotNone(first["next_cursor"])
        second = self.adapter.read_messages(
            principal=self.principal, limit=1, cursor=first["next_cursor"]
        )
        self.assertEqual(len(second["items"]), 1)
        self.assertNotEqual(first["items"][0]["message_id"], second["items"][0]["message_id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
