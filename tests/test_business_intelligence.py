"""Tests for deterministic business intelligence; no external services or actions."""
import pytest

from runtime.papi_core.business_intelligence import (
    BusinessIntelligenceError, analyze_opportunity, build_business_intelligence,
)

BASE = {
    "opportunity_id": "opp-001", "source": "manual", "source_ref": "notes-001",
    "observed_at": "2026-11-12T10:00:00Z", "business_line": "PAPI SERVICES",
    "market": "Senegal", "customer_segment": "small merchants", "offer": "WhatsApp support setup",
    "expected_price_xof": 10000, "variable_cost_xof": 1000,
    "acquisition_cost_xof": 500, "fulfillment_cost_xof": 1500,
    "estimated_monthly_volume": 10, "time_to_first_revenue_days": 14,
    "upfront_cost_xof": 0, "evidence_refs": ["interview-notes-1"], "risk_flags": [],
}


def test_complete_zero_upfront_opportunity_is_only_a_test_candidate():
    result = analyze_opportunity(BASE)
    assert result["recommendation"] == "small_test_candidate"
    assert result["unit_contribution_xof"] == 7000
    assert result["break_even_units"] == 0
    assert result["realized_revenue_xof"] is None
    assert result["scenarios"]["base"]["contribution_xof"] == 70000


def test_missing_data_and_missing_evidence_are_not_filled_in():
    item = {**BASE, "expected_price_xof": None, "evidence_refs": []}
    result = analyze_opportunity(item)
    assert result["recommendation"] == "insufficient_data"
    assert "expected_price_xof" in result["missing_inputs"]
    assert "evidence_refs" in result["missing_inputs"]
    assert result["unit_contribution_xof"] is None


def test_negative_margin_is_rejected():
    item = {**BASE, "expected_price_xof": 1000}
    assert analyze_opportunity(item)["recommendation"] == "reject"


def test_legal_risk_blocks_small_test_recommendation():
    item = {**BASE, "risk_flags": ["legal_regulatory"]}
    assert analyze_opportunity(item)["recommendation"] == "investigate"


@pytest.mark.parametrize("field,value", [
    ("expected_price_xof", -1), ("estimated_monthly_volume", True),
    ("upfront_cost_xof", 2.5), ("risk_flags", ["unknown"]),
])
def test_malformed_inputs_fail_closed(field, value):
    with pytest.raises(BusinessIntelligenceError):
        analyze_opportunity({**BASE, field: value})


def test_duplicate_ids_are_rejected():
    with pytest.raises(BusinessIntelligenceError):
        build_business_intelligence([BASE, BASE])


def test_policy_never_allows_budget_or_execution():
    with pytest.raises(BusinessIntelligenceError):
        build_business_intelligence([BASE], {"default_budget_xof": 100})
    with pytest.raises(BusinessIntelligenceError):
        build_business_intelligence([BASE], {"execution_enabled": True})


def test_action_plan_is_a_proposal_only_and_no_actions_occur():
    result = build_business_intelligence([BASE], {"default_budget_xof": 0,
        "execution_enabled": False, "external_actions_enabled": False})
    assert result["action_plan_candidates"][0]["status"] == "proposal_only"
    assert result["action_plan_candidates"][0]["execution_authorized"] is False
    assert result["controls"]["actions_executed"] == 0
    assert result["controls"]["spending_xof"] == 0
    assert result["controls"]["realized_revenue_recorded"] == 0
