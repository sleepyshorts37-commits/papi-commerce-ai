import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from papi_core.preview_server import PreviewServerError, create_preview_server


class PreviewServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "index.html").write_text("<!doctype html><h1>Preview</h1>", encoding="utf-8")
        (self.root / "styles.css").write_text("body { color: black; }", encoding="utf-8")
        (self.root / "contact").mkdir()
        (self.root / "contact" / "index.html").write_text("<h1>Contact</h1>", encoding="utf-8")
        self.server = create_preview_server(self.root)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.tmp.cleanup()

    def test_serves_root_nested_page_and_assets_with_security_headers(self):
        with urlopen(self.base + "/") as response:
            body = response.read().decode()
            self.assertEqual(response.status, 200)
            self.assertIn("Preview", body)
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
            self.assertIn("script-src 'none'", response.headers["Content-Security-Policy"])
            self.assertEqual(response.headers["Cache-Control"], "no-store")
        with urlopen(self.base + "/contact/") as response:
            self.assertIn("Contact", response.read().decode())
        with urlopen(self.base + "/styles.css") as response:
            self.assertEqual(response.headers.get_content_type(), "text/css")

    def test_rejects_write_methods_and_path_traversal(self):
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            with self.assertRaises(HTTPError) as caught:
                urlopen(Request(self.base + "/", data=b"x", method=method))
            self.assertEqual(caught.exception.code, 405)
        for path in ("/%2e%2e/secret", "/%2e%2e%2fsecret", "/missing.html"):
            with self.assertRaises(HTTPError):
                urlopen(self.base + path)

    def test_rejects_symlink_even_when_target_is_inside_root(self):
        outside = self.root / "styles.css"
        link = self.root / "linked.css"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable on this runner")
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.base + "/linked.css")
        self.assertEqual(caught.exception.code, 404)

    def test_server_refuses_non_loopback_and_invalid_ports(self):
        with self.assertRaises(PreviewServerError):
            create_preview_server(self.root, host="0.0.0.0")
        with self.assertRaises(PreviewServerError):
            create_preview_server(self.root, port=-1)


if __name__ == "__main__":
    unittest.main()
