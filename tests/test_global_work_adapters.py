import json
import unittest

from papi_core.global_work_adapters import (
    GlobalWorkAdapterError, parse_json_api_payload, parse_rss_payload,
)


class ReadOnlyFeedAdapterTests(unittest.TestCase):
    def test_rss_payload_normalized_as_unverified_candidate(self):
        payload = """<?xml version="1.0"?><rss version="2.0"><channel>
          <item><title>Remote writing task</title><link>https://example.org/task</link>
          <description>Write a short product guide</description><pubDate>Thu, 12 Nov 2026 10:00:00 GMT</pubDate></item>
        </channel></rss>"""
        result = parse_rss_payload(payload, source_id="rss-demo")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_url"], "https://example.org/task")
        self.assertEqual(result[0]["qualification_status"], "unverified")
        self.assertFalse(result[0]["application_submitted"])
        self.assertIn("payout_methods", result[0]["missing_fields"])

    def test_rss_rejects_dtd_and_entities(self):
        payload = '<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///etc/passwd">]><rss><channel/></rss>'
        with self.assertRaises(GlobalWorkAdapterError):
            parse_rss_payload(payload, source_id="bad")

    def test_rss_rejects_non_https_item_link(self):
        payload = '<rss><channel><item><title>Task</title><link>http://example.org</link></item></channel></rss>'
        with self.assertRaises(GlobalWorkAdapterError):
            parse_rss_payload(payload, source_id="bad")

    def test_json_api_payload_supports_items_envelope(self):
        payload = json.dumps({"items": [{
            "title": "Data task", "url": "https://example.org/task/2",
            "description": "Review product records", "published_at": "2026-11-12T10:00:00Z",
        }]})
        result = parse_json_api_payload(payload, source_id="api-demo")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["candidate_id"], "api-demo:0")
        self.assertEqual(result[0]["qualification_status"], "unverified")

    def test_json_rejects_invalid_url_and_invalid_json(self):
        with self.assertRaises(GlobalWorkAdapterError):
            parse_json_api_payload('[{"title":"Task","url":"javascript:alert(1)"}]', source_id="bad")
        with self.assertRaises(GlobalWorkAdapterError):
            parse_json_api_payload("{not-json", source_id="bad")

    def test_rejects_local_and_non_public_ip_urls(self):
        for url in ("https://localhost/task", "https://127.0.0.1/task",
                    "https://10.0.0.5/task", "https://[::1]/task",
                    "https://service.internal/task"):
            with self.subTest(url=url), self.assertRaises(GlobalWorkAdapterError):
                parse_json_api_payload(json.dumps([{"title": "Task", "url": url}]), source_id="bad")

    def test_rejects_malformed_port(self):
        with self.assertRaises(GlobalWorkAdapterError):
            parse_json_api_payload('[{"title":"Task","url":"https://example.org:bad/task"}]', source_id="bad")

    def test_payload_size_is_bounded(self):
        with self.assertRaises(GlobalWorkAdapterError):
            parse_json_api_payload(" " * 1_000_001, source_id="large")


if __name__ == "__main__":
    unittest.main()
