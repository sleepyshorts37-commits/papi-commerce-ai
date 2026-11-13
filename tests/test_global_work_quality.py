import unittest
from datetime import datetime, timezone

from papi_core.global_work_quality import (
    GlobalWorkQualityError, assess_candidate_quality, canonicalize_url,
    deduplicate_candidates, evaluate_candidate_freshness, fingerprint_candidate,
)


class GlobalWorkQualityTests(unittest.TestCase):
    def test_canonical_url_removes_tracking_parameters(self):
        self.assertEqual(
            canonicalize_url("https://EXAMPLE.org/jobs/42/?utm_source=x&b=2&a=1"),
            "https://example.org/jobs/42?a=1&b=2",
        )

    def test_deduplicates_tracking_variants(self):
        items = [
            {"title": "Task", "source_url": "https://example.org/job/1?utm_source=a"},
            {"title": "Task copy", "source_url": "https://example.org/job/1?utm_source=b"},
            {"title": "Other", "source_url": "https://example.org/job/2"},
        ]
        result = deduplicate_candidates(items)
        self.assertEqual(result["unique_count"], 2)
        self.assertEqual(result["duplicate_count"], 1)
        self.assertEqual(result["duplicates"][0]["duplicate_of"], 0)

    def test_freshness_states(self):
        now = datetime(2026, 11, 13, tzinfo=timezone.utc)
        self.assertEqual(evaluate_candidate_freshness(
            {"published_at": "2026-11-10T00:00:00Z"}, now=now)["freshness"], "fresh")
        self.assertEqual(evaluate_candidate_freshness(
            {"published_at": "2026-09-01T00:00:00Z"}, now=now)["freshness"], "stale")
        self.assertEqual(evaluate_candidate_freshness({}, now=now)["freshness"], "unknown")
        self.assertEqual(evaluate_candidate_freshness(
            {"published_at": "2026-12-01T00:00:00Z"}, now=now)["freshness"], "future_date")

    def test_quality_never_qualifies_candidate_automatically(self):
        result = assess_candidate_quality({
            "title": "Task", "source_id": "demo",
            "source_url": "https://example.org/task",
            "missing_fields": ["payout_methods", "eligible_countries"],
        })
        self.assertEqual(result["quality"], "incomplete")
        self.assertFalse(result["qualified"])
        self.assertFalse(result["application_submitted"])

    def test_invalid_timezone_and_url_rejected(self):
        with self.assertRaises(GlobalWorkQualityError):
            evaluate_candidate_freshness({"published_at": "2026-11-10T00:00:00"}, now="2026-11-13T00:00:00Z")
        with self.assertRaises(GlobalWorkQualityError):
            fingerprint_candidate({"source_url": "http://example.org/job"})

    def test_canonical_url_rejects_local_hosts_and_non_public_ips(self):
        for url in ("https://localhost/task", "https://127.0.0.1/task",
                    "https://192.168.1.10/task", "https://[::1]/task",
                    "https://host.local/task"):
            with self.subTest(url=url), self.assertRaises(GlobalWorkQualityError):
                canonicalize_url(url)

    def test_canonical_url_rejects_malformed_port(self):
        with self.assertRaises(GlobalWorkQualityError):
            canonicalize_url("https://example.org:invalid/task")

    def test_future_date_never_auto_queued(self):
        result = evaluate_candidate_freshness(
            {"published_at": "2026-11-14T00:00:00Z"},
            now="2026-11-13T00:00:00Z",
        )
        self.assertFalse(result["eligible_for_auto_queue"])


if __name__ == "__main__":
    unittest.main()
