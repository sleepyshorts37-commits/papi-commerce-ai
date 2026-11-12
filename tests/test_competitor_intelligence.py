"""Tests for evidence-based competitor intelligence."""
from runtime.papi_core.competitor_intelligence import (
    CompetitorIntelligenceError, analyze_competitor_observations,
)

BASE = {
    "competitor_name": "Example Shop", "market": "Senegal",
    "offer": "Monthly customer support service",
    "source_type": "official_public_page",
    "source_url": "https://example.com/pricing",
    "observed_at": "2026-11-12T09:00:00Z",
    "price_xof": 15000, "currency": "XOF",
}


def test_competitor_price_comparison_is_explicit():
    result = analyze_competitor_observations(
        [BASE], as_of="2026-11-12T10:00:00Z", own_price_xof=10000
    )
    row = result["observations"][0]
    assert row["price_difference_vs_own_xof"] == 5000
    assert row["price_difference_vs_own_percent"] == 50.0
    assert row["fresh"] is True
    assert row["evidence_status"].endswith("not_fetched_or_verified")


def test_unknown_price_remains_unknown():
    result = analyze_competitor_observations(
        [{**BASE, "price_xof": None}], as_of="2026-11-12T10:00:00Z",
        own_price_xof=10000,
    )
    assert result["observations"][0]["price_difference_vs_own_xof"] is None


def test_non_xof_prices_are_rejected():
    result = analyze_competitor_observations(
        [{**BASE, "currency": "EUR"}], as_of="2026-11-12T10:00:00Z"
    )
    assert result["observations_rejected"] == 1


def test_future_observation_is_rejected():
    result = analyze_competitor_observations(
        [{**BASE, "observed_at": "2026-11-13T10:00:00Z"}],
        as_of="2026-11-12T10:00:00Z",
    )
    assert result["observations_rejected"] == 1


def test_non_https_or_credential_urls_are_rejected():
    for url in ("http://example.com", "https://user:pass@example.com"):
        result = analyze_competitor_observations(
            [{**BASE, "source_url": url}], as_of="2026-11-12T10:00:00Z"
        )
        assert result["observations_rejected"] == 1


def test_unknown_source_type_is_rejected():
    result = analyze_competitor_observations(
        [{**BASE, "source_type": "rumor"}], as_of="2026-11-12T10:00:00Z"
    )
    assert result["observations_rejected"] == 1


def test_stale_observation_is_flagged():
    result = analyze_competitor_observations(
        [BASE], as_of="2027-01-01T00:00:00Z", freshness_days=30
    )
    assert result["observations"][0]["fresh"] is False
    assert result["observations"][0]["confidence"] == "low"


def test_no_external_action_or_network_is_performed():
    result = analyze_competitor_observations(
        [BASE], as_of="2026-11-12T10:00:00Z"
    )
    assert result["controls"]["network_requests"] == 0
    assert result["controls"]["pages_fetched"] == 0
    assert result["controls"]["spending_xof"] == 0
    assert result["controls"]["actions_executed"] == 0
