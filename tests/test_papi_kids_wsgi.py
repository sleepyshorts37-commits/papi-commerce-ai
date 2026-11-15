import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from papi_core.papi_kids_wsgi import create_app


class PapiKidsWSGICompositionTests(unittest.TestCase):
    def test_composes_api_with_private_storage_and_health_route(self):
        with tempfile.TemporaryDirectory() as root:
            with patch.dict("os.environ", {"PAPI_KIDS_REVIEWER_ID": "editor-01"}):
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

    def test_refuses_missing_private_storage(self):
        with self.assertRaises(RuntimeError):
            create_app(storage_root="", connection_factory=lambda: None)


if __name__ == "__main__":
    unittest.main()
