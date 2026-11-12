"""Tests for safe opportunity signal intake and deterministic triage."""
import pytest

from runtime.papi_core.opportunity_scanner import (
    OpportunityScannerError, scan_opportunity_signals,
)

BASE = {
    "source": "manual interview", "source_ref": "interview-001",
    "observed_at": "2026-11-12T09:00:00Z", "business_line": "PAPI SERVICES",
    "market": "Senegal", "customer_segment": "small shops",
    "offer": "WhatsApp customer support setup",
    "problem_observed": "Merchants miss incoming order requests",
    "proposed_solution": "Configure a customer response assistant",
    "expected_price_xof": 10000, "estimated_monthly_volume": 5,
}


def test_complete_signal_is_ranked_for_business_analysis():
    result = scan_opportunity_signals([BASE], as_of="2026-11-12T10:00:00Z")
    signal = result["signals"][0]
    assert signal["triage_status"] == "ready_for_business_analysis"
    assert signal["missing_fields"] == []
    assert signal["evidence_status"] == "source_reference_provided_not_verified"


def test_incomplete_signal_is_not_fabricated():
    item = {key: value for key, value in BASE.items()
            if key not in {"problem_observed", "expected_price_xof"}}
    result = scan_opportunity_signals([item], as_of="2026-11-12T10:00:00Z")
    assert result["signals"][0]["triage_status"] == "needs_enrichment"
    assert "problem_observed" in result["signals"][0]["missing_fields"]


def test_duplicate_signals_are_deduplicated():
    result = scan_opportunity_signals([BASE, BASE], as_of="2026-11-12T10:00:00Z")
    assert result["signals_accepted"] == 1
    assert result["duplicates_skipped"] == 1


def test_old_signal_is_marked_stale():
    result = scan_opportunity_signals([BASE], as_of="2027-01-01T00:00:00Z")
    assert result["signals"][0]["triage_status"] == "stale"


def test_future_signal_is_rejected():
    result = scan_opportunity_signals([BASE], as_of="2026-11-11T00:00:00Z")
    assert result["signals_rejected"] == 1
    assert "future" in result["rejections"][0]["reason"]


@pytest.mark.parametrize("field,value", [
    ("business_line", "UNKNOWN"), ("expected_price_xof", True),
    ("estimated_monthly_volume", -1), ("source_ref", "private email"),
])
def test_invalid_or_sensitive_input_is_rejected(field, value):
    result = scan_opportunity_signals([{**BASE, field: value}], as_of="2026-11-12T10:00:00Z")
    assert result["signals_rejected"] == 1
    assert result["signals_accepted"] == 0


def test_unknown_fields_fail_closed():
    result = scan_opportunity_signals([{**BASE, "raw_customer_data": "x"}],
                                      as_of="2026-11-12T10:00:00Z")
    assert result["signals_rejected"] == 1


def test_scanner_never_performs_network_or_actions():
    result = scan_opportunity_signals([BASE], as_of="2026-11-12T10:00:00Z")
    assert result["controls"]["network_requests"] == 0
    assert result["controls"]["spending_xof"] == 0
    assert result["controls"]["actions_executed"] == 0
