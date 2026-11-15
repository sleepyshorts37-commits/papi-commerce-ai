import io
import json
import tempfile
import unittest
from pathlib import Path

from papi_core.papi_kids_wsgi import create_app


class FakeCursor:
    def __init__(self, row=(1,)):
        self.row = row
        self.closed = False
    def execute(self, query):
        if query != "SELECT 1":
            raise AssertionError("Unexpected readiness query")
    def fetchone(self):
        return self.row
    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, row=(1,), fail=False):
        self.cursor_obj = FakeCursor(row)
        self.fail = fail
        self.closed = False
    def cursor(self):
        if self.fail:
            raise RuntimeError("database offline")
        return self.cursor_obj
    def close(self):
        self.closed = True


class PapiKidsWSGICompositionTests(unittest.TestCase):
    def test_composes_api_with_private_storage_and_health_route(self):
        with tempfile.TemporaryDirectory() as root:
            app = create_app(storage_root=Path(root) / "private", connection_factory=lambda: None)
            environ = {"PATH_INFO": "/healthz", "REQUEST_METHOD": "GET"}
            captured = {}
            def start_response(status, headers):
                captured["status"] = status
                captured["headers"] = headers
            payload = b"".join(app(environ, start_response))
            self.assertEqual(captured["status"], "200 OK")
            self.assertIn(b'"service": "papi-kids"', payload)
            self.assertEqual((Path(root) / "private").stat().st_mode & 0o777, 0o700)

    def test_readyz_requires_database_and_private_storage(self):
        with tempfile.TemporaryDirectory() as root:
            connection = FakeConnection()
            app = create_app(
                storage_root=Path(root) / "private",
                connection_factory=lambda: connection,
            )
            environ = {"PATH_INFO": "/readyz", "REQUEST_METHOD": "GET"}
            captured = {}
            def start_response(status, headers):
                captured["status"] = status
            payload = json.loads(b"".join(app(environ, start_response)))
            self.assertEqual(captured["status"], "200 OK")
            self.assertEqual(payload["status"], "ready")
            self.assertTrue(payload["components"]["database"])
            self.assertTrue(payload["components"]["private_storage"])
            self.assertTrue(connection.closed)
            self.assertTrue(connection.cursor_obj.closed)

    def test_readyz_returns_503_without_database(self):
        with tempfile.TemporaryDirectory() as root:
            app = create_app(
                storage_root=Path(root) / "private",
                connection_factory=lambda: FakeConnection(fail=True),
            )
            environ = {"PATH_INFO": "/readyz", "REQUEST_METHOD": "GET"}
            captured = {}
            def start_response(status, headers):
                captured["status"] = status
            payload = json.loads(b"".join(app(environ, start_response)))
            self.assertEqual(captured["status"], "503 Service Unavailable")
            self.assertEqual(payload["status"], "not_ready")
            self.assertFalse(payload["components"]["database"])

    def test_refuses_missing_private_storage(self):
        with self.assertRaises(RuntimeError):
            create_app(storage_root="", connection_factory=lambda: None)


if __name__ == "__main__":
    unittest.main()
