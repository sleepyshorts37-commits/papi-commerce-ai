"""Tests for aggregated sales-channel intelligence."""
from runtime.papi_core.sales_intelligence import analyze_sales_channels

BASE = {
    "business_line": "PAPI SERVICES", "market": "Senegal",
    "customer_segment": "small hotels", "offer": "WhatsApp customer support",
    "channel": "whatsapp", "source_type": "manual_count",
    "source_url": "https://example.com/report",
    "observed_at": "2026-11-12T09:00:00Z",
    "inquiries_count": 20, "qualified_count": 10, "sales_count": 4,
    "campaign_spend_xof": 5000, "observation_window_days": 14,
}


def test_channel_metrics_are_calculated_from_observed_counts():
    result = analyze_sales_channels([BASE], as_of="2026-11-12T10:00:00Z")
    row = result["observations"][0]
    assert row["qualification_rate_percent"] == 50.0
    assert row["qualified_to_sale_rate_percent"] == 40.0
    assert row["cost_per_qualified_lead_xof"] == 500.0


def test_missing_counts_remain_unknown():
    item = {key: value for key, value in BASE.items()
            if key not in {"qualified_count", "sales_count", "campaign_spend_xof"}}
    row = analyze_sales_channels([item], as_of="2026-11-12T10:00:00Z")["observations"][0]
    assert row["qualification_rate_percent"] is None
    assert row["qualified_to_sale_rate_percent"] is None
    assert row["cost_per_qualified_lead_xof"] is None


def test_future_observation_is_rejected():
    result = analyze_sales_channels(
        [{**BASE, "observed_at": "2026-11-13T00:00:00Z"}],
        as_of="2026-11-12T10:00:00Z",
    )
    assert result["observations_rejected"] == 1


def test_invalid_business_line_and_channel_are_rejected():
    for changes in ({"business_line": "UNKNOWN"}, {"channel": "secret_dm"}):
        result = analyze_sales_channels([{**BASE, **changes}],
                                        as_of="2026-11-12T10:00:00Z")
        assert result["observations_rejected"] == 1


def test_personal_contact_data_is_rejected():
    result = analyze_sales_channels([{**BASE, "customer_segment": "client@example.com"}],
                                    as_of="2026-11-12T10:00:00Z")
    assert result["observations_rejected"] == 1


def test_inconsistent_counts_are_rejected():
    result = analyze_sales_channels([{**BASE, "qualified_count": 21}],
                                    as_of="2026-11-12T10:00:00Z")
    assert result["observations_rejected"] == 1


def test_stale_observations_are_not_ranked_as_current_channels():
    result = analyze_sales_channels([BASE], as_of="2027-01-01T00:00:00Z")
    comparison = result["channel_comparisons"][0]
    assert comparison["fresh_channel_observations"] == 0
    assert comparison["best_observed_channel"] is None


def test_no_outreach_or_spending():
    result = analyze_sales_channels([BASE], as_of="2026-11-12T10:00:00Z")
    assert result["controls"]["prospects_contacted"] == 0
    assert result["controls"]["messages_sent"] == 0
    assert result["controls"]["campaigns_launched"] == 0
    assert result["controls"]["spending_xof"] == 0
