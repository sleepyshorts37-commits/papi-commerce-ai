import unittest

from papi_core.global_work_sources import (
    GlobalWorkSourceError, ingest_records, validate_source_registry,
)


def source_registry(**overrides):
    source = {
        "id": "official-catalogue",
        "name": "Example official catalogue",
        "kind": "official_api",
        "access_policy": "allowed",
        "enabled": True,
        "terms_url": "https://example.org/terms",
        "allowed_countries": ["SN"],
        "notes": "Fixture only; not a real platform integration.",
    }
    source.update(overrides)
    return {"project": "PAPI COMMERCE AI", "schema_version": "1.0", "sources": [source]}


def opportunity(**overrides):
    item = {
        "id": "task-001", "source_url": "https://example.org/task/1",
        "title": "Product data review", "description": "Review public product data.",
        "country_eligibility": "Worldwide", "eligible_countries": ["SN"],
        "compensation_amount": 10, "currency": "USD", "estimated_minutes": 30,
        "upfront_cost": 0, "automation_policy": "allowed", "ai_policy": "allowed",
        "human_presence_required": False, "payout_methods": ["PayPal"],
    }
    item.update(overrides)
    return item


class SourceRegistryTests(unittest.TestCase):
    def test_valid_registry(self):
        self.assertEqual(validate_source_registry(source_registry()), [])

    def test_duplicate_source_ids_rejected(self):
        registry = source_registry()
        registry["sources"].append(dict(registry["sources"][0]))
        self.assertTrue(any("dupliqué" in error for error in validate_source_registry(registry)))

    def test_unknown_fields_rejected(self):
        registry = source_registry()
        registry["sources"][0]["api_key"] = "never-store"
        self.assertTrue(validate_source_registry(registry))


class SourceIngestionTests(unittest.TestCase):
    def test_authorized_prefetched_record_keeps_provenance(self):
        result = ingest_records(
            source_registry(), source_id="official-catalogue",
            fetched_at="2026-11-13T12:00:00Z", records=[opportunity()],
        )
        self.assertEqual(len(result["accepted"]), 1)
        self.assertEqual(result["accepted"][0]["provenance"]["source_id"], "official-catalogue")
        self.assertFalse(result["external_fetch_performed"])
        self.assertFalse(result["application_submitted"])

    def test_duplicate_opportunity_rejected(self):
        result = ingest_records(
            source_registry(), source_id="official-catalogue",
            fetched_at="2026-11-13T12:00:00Z",
            records=[opportunity(), opportunity()],
        )
        self.assertEqual(len(result["accepted"]), 1)
        self.assertEqual(len(result["rejected"]), 1)

    def test_invalid_record_rejected_without_blocking_valid_record(self):
        result = ingest_records(
            source_registry(), source_id="official-catalogue",
            fetched_at="2026-11-13T12:00:00Z",
            records=[opportunity(source_url="http://unsafe.example"), opportunity(id="task-002")],
        )
        self.assertEqual(len(result["accepted"]), 1)
        self.assertEqual(len(result["rejected"]), 1)

    def test_disabled_or_review_source_fails_closed(self):
        for overrides in ({"enabled": False}, {"access_policy": "owner_review"}, {"access_policy": "prohibited"}):
            with self.subTest(overrides=overrides):
                with self.assertRaises(GlobalWorkSourceError):
                    ingest_records(
                        source_registry(**overrides), source_id="official-catalogue",
                        fetched_at="2026-11-13T12:00:00Z", records=[],
                    )

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(GlobalWorkSourceError):
            ingest_records(
                source_registry(), source_id="official-catalogue",
                fetched_at="2026-11-13T12:00:00", records=[],
            )


if __name__ == "__main__":
    unittest.main()
