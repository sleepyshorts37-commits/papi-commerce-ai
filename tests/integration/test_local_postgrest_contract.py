"""Live PostgREST contract checks against the disposable local stack only.

Requires the local PostgreSQL schema and migrations 004/005 to be applied first.
No hosted Supabase URL, project key, or customer data is accepted by this harness.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


BASE_URL = os.environ.get("PAPI_LOCAL_REST_URL", "http://127.0.0.1:55433").rstrip("/")
JWT_SECRET = os.environ.get(
    "PAPI_LOCAL_JWT_SECRET",
    "papi_local_only_jwt_secret_change_before_any_nonlocal_use",
)


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def service_token() -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = b64url(json.dumps({
        "role": "service_role",
        "iss": "papi-local-contract-test",
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
    }).encode())
    signing_input = f"{header}.{payload}".encode()
    import hashlib
    import hmac
    signature = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{b64url(signature)}"


def request(method: str, path: str, payload: dict | None = None, prefer: str | None = None):
    headers = {
        "Authorization": f"Bearer {service_token()}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as response:
        body = response.read()
        return response.status, json.loads(body) if body else None


def main() -> None:
    if not BASE_URL.startswith("http://127.0.0.1:") and not BASE_URL.startswith("http://localhost:"):
        raise SystemExit("Refusing non-loopback REST URL; this test is local-only.")
    if len(JWT_SECRET) < 32:
        raise SystemExit("Local JWT secret must contain at least 32 characters.")

    recipient = f"ci_{uuid.uuid4().hex[:12]}"
    message_id = f"MSG-{uuid.uuid4().hex.upper()}"
    idem = f"papi-rest-{uuid.uuid4().hex}"
    row = {
        "message_id": message_id,
        "sent_at": "2026-01-01T00:00:00Z",
        "sender": "ci-agent",
        "recipient": recipient,
        "subject": "PostgREST live contract",
        "body": "Disposable local integration test.",
        "message_type": "info",
        "idempotency_key": idem,
    }

    status, inserted = request(
        "POST",
        "/papi_chat_messages?on_conflict=idempotency_key",
        row,
        "resolution=ignore-duplicates,return=representation",
    )
    assert status in (200, 201), f"Unexpected insert status: {status}"
    assert inserted and inserted[0]["message_id"] == message_id, "Insert representation mismatch"

    query = urllib.parse.urlencode({
        "select": "message_id,recipient",
        "recipient": f"eq.{recipient}",
        "limit": "5",
    })
    status, rows = request("GET", f"/papi_chat_messages?{query}")
    assert status == 200 and len(rows) == 1, "Recipient-filtered read did not return exactly one row"
    assert rows[0]["message_id"] == message_id and rows[0]["recipient"] == recipient

    try:
        request("PATCH", f"/papi_chat_messages?message_id=eq.{message_id}", {"subject": "tamper"})
    except urllib.error.HTTPError as exc:
        assert exc.code in (401, 403, 405, 409, 500), f"Unexpected mutation response: {exc.code}"
    else:
        raise AssertionError("Append-only message unexpectedly allowed PATCH")

    print("PASS: PostgREST JWT auth, insert, recipient filter, and append-only guard")


if __name__ == "__main__":
    main()
