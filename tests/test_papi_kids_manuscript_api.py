import io, json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from papi_core.papi_kids_manuscript_api import create_papi_kids_manuscript_app

TOKEN = "test-token-" + "x" * 40

def call(app, *, token=TOKEN, body=b"# Mon livre\n", filename="manuscrit.md",
         scheme="https", method="POST", path="/api/papi-kids/manuscripts"):
    environ = {"PATH_INFO": path, "REQUEST_METHOD": method, "wsgi.url_scheme": scheme,
        "HTTP_AUTHORIZATION": "Bearer " + token if token else "", "HTTP_X_FILENAME": filename,
        "CONTENT_TYPE": "text/markdown", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
    captured = {}
    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)
    payload = b"".join(app(environ, start_response))
    return captured, json.loads(payload)

class PapiKidsManuscriptAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = create_papi_kids_manuscript_app(storage_root=self.temp.name)

    def test_upload_requires_authentication_and_tls(self):
        with patch.dict(os.environ, {"PAPI_KIDS_UPLOAD_TOKEN": TOKEN}, clear=True):
            response, _ = call(self.app, token="wrong")
            self.assertEqual(response["status"], "401 Unauthorized")
            response, _ = call(self.app, scheme="http")
            self.assertEqual(response["status"], "403 Forbidden")

    def test_upload_persists_private_file_and_hash_metadata(self):
        content = b"# Nia\n\nUne histoire."
        with patch.dict(os.environ, {"PAPI_KIDS_UPLOAD_TOKEN": TOKEN}, clear=True):
            response, data = call(self.app, body=content)
        self.assertEqual(response["status"], "201 Created")
        folder = Path(self.temp.name) / data["upload_id"]
        stored = folder / "manuscript.md"
        self.assertEqual(stored.read_bytes(), content)
        self.assertEqual(stored.stat().st_mode & 0o777, 0o600)
        meta = json.loads((folder / "metadata.json").read_text())
        self.assertEqual(meta["sha256"], data["sha256"])
        self.assertEqual(meta["status"], "queued_for_analysis")
        job = json.loads((folder / "job.json").read_text())
        self.assertEqual(job["status"], "queued_for_analysis")
        self.assertFalse(job["ai_invoked"])
        self.assertFalse(job["provider_invoked"])

    def test_identical_upload_is_idempotent(self):
        content = b"# Same manuscript"
        with patch.dict(os.environ, {"PAPI_KIDS_UPLOAD_TOKEN": TOKEN}, clear=True):
            first_response, first = call(self.app, body=content)
            second_response, second = call(self.app, body=content)
        self.assertEqual(first_response["status"], "201 Created")
        self.assertEqual(second_response["status"], "200 OK")
        self.assertEqual(first["upload_id"], second["upload_id"])
        self.assertTrue(second["deduplicated"])
        self.assertEqual(len(list(Path(self.temp.name).glob("PKP-UP-*"))), 1)

    def test_duplicate_upload_retries_failed_postgres_registration(self):
        attempts = []
        def registrar(metadata):
            attempts.append(metadata["upload_id"])
            if len(attempts) == 1:
                raise RuntimeError("database temporarily unavailable")
            return {"book_id": "book-1", "job_id": 19, "status": "queued_for_analysis"}
        app = create_papi_kids_manuscript_app(storage_root=self.temp.name, queue_registrar=registrar)
        with patch.dict(os.environ, {"PAPI_KIDS_UPLOAD_TOKEN": TOKEN}, clear=True):
            first_response, first = call(app, body=b"# Retry me")
            second_response, second = call(app, body=b"# Retry me")
        self.assertEqual(first_response["status"], "503 Service Unavailable")
        self.assertTrue(first["retryable"])
        self.assertEqual(second_response["status"], "200 OK")
        self.assertEqual(second["persistence_status"], "registered")
        self.assertEqual(len(attempts), 2)
        metadata = json.loads((Path(self.temp.name) / second["upload_id"] / "metadata.json").read_text())
        self.assertEqual(metadata["postgres_queue"]["job_id"], 19)

    def test_authenticated_library_endpoint_returns_book_summaries(self):
        app = create_papi_kids_manuscript_app(
            storage_root=self.temp.name,
            library_reader=lambda: [{"upload_id": "PKP-UP-" + "a" * 32,
                "title": "Nia", "book_status": "queued_for_analysis",
                "job_status": "queued", "illustration_count": 0,
                "approved_illustration_count": 0}],
        )
        with patch.dict(os.environ, {"PAPI_KIDS_UPLOAD_TOKEN": TOKEN}, clear=True):
            response, payload = call(app, method="GET", path="/api/papi-kids/manuscripts")
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(payload["books"][0]["title"], "Nia")

    def test_authenticated_status_endpoint_returns_sanitized_record(self):
        upload_id = "PKP-UP-" + "a" * 32
        reader_calls = []
        def reader(value):
            reader_calls.append(value)
            return {"upload_id": value, "book_status": "queued_for_analysis",
                    "job": {"job_id": 23, "status": "queued", "attempts": 0, "max_attempts": 5}}
        app = create_papi_kids_manuscript_app(storage_root=self.temp.name, status_reader=reader)
        with patch.dict(os.environ, {"PAPI_KIDS_UPLOAD_TOKEN": TOKEN}, clear=True):
            response, payload = call(app, method="GET", path="/api/papi-kids/manuscripts/" + upload_id)
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(payload["job"]["job_id"], 23)
        self.assertEqual(reader_calls, [upload_id])

    def test_status_endpoint_fails_closed_when_reader_missing(self):
        upload_id = "PKP-UP-" + "b" * 32
        with patch.dict(os.environ, {"PAPI_KIDS_UPLOAD_TOKEN": TOKEN}, clear=True):
            response, payload = call(self.app, method="GET", path="/api/papi-kids/manuscripts/" + upload_id)
        self.assertEqual(response["status"], "503 Service Unavailable")
        self.assertEqual(payload["error"], "status_not_configured")

    def test_review_endpoint_requires_separate_review_token_and_records_server_reviewer(self):
        asset_id = "PKP-ASSET-" + "a" * 24
        received = []
        def handler(asset, decision, reviewer, notes):
            received.append((asset, decision, reviewer, notes))
            return {"asset_id": asset, "review_status": decision}
        app = create_papi_kids_manuscript_app(
            storage_root=self.temp.name, review_handler=handler)
        body = json.dumps({"decision": "approved", "notes": "Cohérent"}).encode()
        environ = {
            "PATH_INFO": "/api/papi-kids/assets/" + asset_id + "/review",
            "REQUEST_METHOD": "POST", "wsgi.url_scheme": "https",
            "HTTP_AUTHORIZATION": "Bearer " + TOKEN,
            "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
        }
        captured = {}
        def start_response(status, headers):
            captured["status"] = status
        with patch.dict(os.environ, {
            "PAPI_KIDS_REVIEW_TOKEN": TOKEN, "PAPI_KIDS_REVIEWER_ID": "owner-01"
        }, clear=True):
            payload = json.loads(b"".join(app(environ, start_response)))
        self.assertEqual(captured["status"], "200 OK")
        self.assertEqual(payload["review_status"], "approved")
        self.assertEqual(received, [(asset_id, "approved", "owner-01", "Cohérent")])

    def test_safety_review_endpoint_uses_distinct_token_and_server_reviewer(self):
        upload_id = "PKP-UP-" + "a" * 32
        received = []
        def handler(upload, digest, decision, reviewer, notes):
            received.append((upload, digest, decision, reviewer, notes))
            return {"upload_id": upload, "approved": decision == "approved"}
        app = create_papi_kids_manuscript_app(
            storage_root=self.temp.name, safety_review_handler=handler,
        )
        digest = "b" * 64
        body = json.dumps({
            "decision": "approved", "manuscript_sha256": digest,
            "notes": "Le passage a été vérifié et validé par un adulte.",
        }).encode()
        environ = {
            "PATH_INFO": "/api/papi-kids/manuscripts/" + upload_id + "/safety-review",
            "REQUEST_METHOD": "POST", "wsgi.url_scheme": "https",
            "HTTP_AUTHORIZATION": "Bearer " + TOKEN,
            "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
        }
        captured = {}
        def start_response(status, headers):
            captured["status"] = status
        with patch.dict(os.environ, {
            "PAPI_KIDS_SAFETY_REVIEW_TOKEN": TOKEN,
            "PAPI_KIDS_REVIEWER_ID": "owner-01",
        }, clear=True):
            payload = json.loads(b"".join(app(environ, start_response)))
        self.assertEqual(captured["status"], "200 OK")
        self.assertTrue(payload["approved"])
        self.assertEqual(received, [(
            upload_id, digest, "approved", "owner-01",
            "Le passage a été vérifié et validé par un adulte.",
        )])

    def test_kdp_metadata_endpoint_uses_separate_token_and_server_editor(self):
        upload_id = "PKP-UP-" + "a" * 32
        received = []
        def saver(upload, metadata, editor):
            received.append((upload, metadata, editor))
            return {"upload_id": upload, "status": "incomplete", "blocker_count": 4}
        app = create_papi_kids_manuscript_app(
            storage_root=self.temp.name, metadata_saver=saver,
        )
        metadata = {"title": "Nia et la rivière", "language": "fr"}
        body = json.dumps({"metadata": metadata}).encode()
        environ = {
            "PATH_INFO": "/api/papi-kids/manuscripts/" + upload_id + "/kdp-metadata",
            "REQUEST_METHOD": "POST", "wsgi.url_scheme": "https",
            "HTTP_AUTHORIZATION": "Bearer " + TOKEN,
            "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
        }
        captured = {}
        def start_response(status, headers):
            captured["status"] = status
        with patch.dict(os.environ, {
            "PAPI_KIDS_METADATA_TOKEN": TOKEN,
            "PAPI_KIDS_METADATA_EDITOR_ID": "owner-01",
        }, clear=True):
            payload = json.loads(b"".join(app(environ, start_response)))
        self.assertEqual(captured["status"], "200 OK")
        self.assertEqual(payload["status"], "incomplete")
        self.assertEqual(received, [(upload_id, metadata, "owner-01")])

    def test_metadata_endpoint_does_not_reuse_safety_review_token(self):
        upload_id = "PKP-UP-" + "b" * 32
        body = json.dumps({"metadata": {"title": "Nia"}}).encode()
        environ = {
            "PATH_INFO": "/api/papi-kids/manuscripts/" + upload_id + "/kdp-metadata",
            "REQUEST_METHOD": "POST", "wsgi.url_scheme": "https",
            "HTTP_AUTHORIZATION": "Bearer " + TOKEN,
            "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
        }
        captured = {}
        def start_response(status, headers):
            captured["status"] = status
        with patch.dict(os.environ, {
            "PAPI_KIDS_SAFETY_REVIEW_TOKEN": TOKEN,
            "PAPI_KIDS_METADATA_EDITOR_ID": "owner-01",
        }, clear=True):
            b"".join(self.app(environ, start_response))
        self.assertEqual(captured["status"], "503 Service Unavailable")

    def test_safety_review_token_is_distinct_from_illustration_review_token(self):
        upload_id = "PKP-UP-" + "b" * 32
        body = json.dumps({
            "decision": "approved", "manuscript_sha256": "c" * 64, "notes": "",
        }).encode()
        environ = {
            "PATH_INFO": "/api/papi-kids/manuscripts/" + upload_id + "/safety-review",
            "REQUEST_METHOD": "POST", "wsgi.url_scheme": "https",
            "HTTP_AUTHORIZATION": "Bearer " + TOKEN,
            "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
        }
        captured = {}
        def start_response(status, headers):
            captured["status"] = status
        with patch.dict(os.environ, {
            "PAPI_KIDS_REVIEW_TOKEN": TOKEN, "PAPI_KIDS_REVIEWER_ID": "owner-01",
        }, clear=True):
            b"".join(self.app(environ, start_response))
        self.assertEqual(captured["status"], "503 Service Unavailable")

    def test_review_route_fails_closed_without_review_handler(self):
        asset_id = "PKP-ASSET-" + "b" * 24
        body = b'{"decision":"approved"}'
        environ = {
            "PATH_INFO": "/api/papi-kids/assets/" + asset_id + "/review",
            "REQUEST_METHOD": "POST", "wsgi.url_scheme": "https",
            "HTTP_AUTHORIZATION": "Bearer " + TOKEN,
            "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
        }
        captured = {}
        def start_response(status, headers):
            captured["status"] = status
        with patch.dict(os.environ, {"PAPI_KIDS_REVIEW_TOKEN": TOKEN}, clear=True):
            b"".join(self.app(environ, start_response))
        self.assertEqual(captured["status"], "503 Service Unavailable")

    def test_rejects_bad_filename_size_and_non_utf8(self):
        with patch.dict(os.environ, {"PAPI_KIDS_UPLOAD_TOKEN": TOKEN}, clear=True):
            response, _ = call(self.app, filename="../evil.md")
            self.assertEqual(response["status"], "400 Bad Request")
            response, _ = call(self.app, body=b"x" * (2 * 1024 * 1024 + 1))
            self.assertEqual(response["status"], "413 Payload Too Large")
            response, _ = call(self.app, body=b"\xff")
            self.assertEqual(response["status"], "400 Bad Request")

    def test_unknown_route_and_missing_secret_fail_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            response, _ = call(self.app)
            self.assertEqual(response["status"], "503 Service Unavailable")
        with patch.dict(os.environ, {"PAPI_KIDS_UPLOAD_TOKEN": TOKEN}, clear=True):
            response, _ = call(self.app, path="/other")
            self.assertEqual(response["status"], "404 Not Found")

if __name__ == "__main__":
    unittest.main()
