"""Tests for product sourcing intelligence."""
from runtime.papi_core.product_intelligence import analyze_product_options

BASE = {
    "product_name": "Rechargeable desk lamp", "market": "Senegal",
    "supplier_name": "Supplier A", "source_type": "official_supplier_page",
    "source_url": "https://example.com/lamp",
    "observed_at": "2026-11-12T09:00:00Z",
    "purchase_cost_xof": 5000, "shipping_cost_xof": 500,
    "tax_cost_xof": 0, "packaging_cost_xof": 200, "platform_fee_xof": 300,
    "selling_price_xof": 9000, "minimum_order_quantity": 5,
}


def test_complete_unit_economics():
    result = analyze_product_options([BASE], as_of="2026-11-12T10:00:00Z")
    row = result["products"][0]
    assert row["fully_loaded_unit_cost_xof"] == 6000
    assert row["gross_profit_per_unit_xof"] == 3000
    assert row["gross_margin_percent"] == 33.33
    assert row["recommendation"] == "evaluate_sample_and_supplier"


def test_missing_costs_do_not_get_assumed_zero():
    incomplete = {key: value for key, value in BASE.items() if key != "shipping_cost_xof"}
    row = analyze_product_options([incomplete], as_of="2026-11-12T10:00:00Z")["products"][0]
    assert row["fully_loaded_unit_cost_xof"] is None
    assert row["gross_profit_per_unit_xof"] is None


def test_user_target_price_can_be_used_when_supplier_price_absent():
    item = {key: value for key, value in BASE.items() if key != "selling_price_xof"}
    row = analyze_product_options([item], as_of="2026-11-12T10:00:00Z",
                                  target_selling_price_xof=9000)["products"][0]
    assert row["selling_price_source"] == "user_target"
    assert row["gross_profit_per_unit_xof"] == 3000


def test_non_xof_currency_rejected():
    result = analyze_product_options([{**BASE, "currency": "USD"}],
                                     as_of="2026-11-12T10:00:00Z")
    assert result["observations_rejected"] == 1


def test_http_url_rejected():
    result = analyze_product_options([{**BASE, "source_url": "http://example.com"}],
                                     as_of="2026-11-12T10:00:00Z")
    assert result["observations_rejected"] == 1


def test_future_observation_rejected():
    result = analyze_product_options([{**BASE, "observed_at": "2026-11-13T00:00:00Z"}],
                                     as_of="2026-11-12T10:00:00Z")
    assert result["observations_rejected"] == 1


def test_personal_data_in_supplier_field_rejected():
    result = analyze_product_options([{**BASE, "supplier_name": "seller@example.com"}],
                                     as_of="2026-11-12T10:00:00Z")
    assert result["observations_rejected"] == 1


def test_stale_supplier_quote_not_recommended_for_sample():
    result = analyze_product_options([BASE], as_of="2027-01-01T00:00:00Z")
    row = result["products"][0]
    assert row["fresh"] is False
    assert row["recommendation"] == "collect_missing_costs_or_verify_source"


def test_no_external_actions():
    result = analyze_product_options([BASE], as_of="2026-11-12T10:00:00Z")
    assert result["controls"]["network_requests"] == 0
    assert result["controls"]["supplier_contacts"] == 0
    assert result["controls"]["purchases"] == 0
    assert result["controls"]["spending_xof"] == 0
