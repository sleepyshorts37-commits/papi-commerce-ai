from runtime.papi_core.marketing_growth import analyze_marketing_campaigns


def campaign(**overrides):
    data = {
        "campaign_id": "CMP-001", "business_line": "PAPI MARKET", "channel": "whatsapp",
        "objective": "sales", "period_start": "2026-11-01", "period_end": "2026-11-10",
        "impressions": 1000, "clicks": 100, "leads": 20, "orders": 5,
        "spend_xof": 2000, "paid_revenue_xof": 15000,
        "revenue_evidence_status": "provider_confirmed",
    }
    data.update(overrides)
    return data


def test_calculates_campaign_funnel_and_roas_with_marked_evidence():
    result = analyze_marketing_campaigns([campaign()])
    item = result["campaigns"][0]
    assert item["ctr_percent"] == 10
    assert item["lead_to_order_percent"] == 25
    assert item["roas"] == 7.5


def test_does_not_calculate_roas_for_unverified_revenue():
    result = analyze_marketing_campaigns([campaign(revenue_evidence_status="declared")])
    assert result["campaigns"][0]["roas"] is None


def test_rejects_personal_data_fields():
    result = analyze_marketing_campaigns([campaign(customer_phone="+221700000000")])
    assert result["campaigns_rejected"] == 1


def test_rejects_duplicate_campaign_ids():
    result = analyze_marketing_campaigns([campaign(), campaign()])
    assert result["campaigns_analyzed"] == 1
    assert result["campaigns_rejected"] == 1


def test_rejects_impossible_funnel_and_negative_budget():
    result = analyze_marketing_campaigns([campaign(clicks=1001)])
    assert result["campaigns_rejected"] == 1
    try:
        analyze_marketing_campaigns([], monthly_budget_xof=-1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative budget must be rejected")


def test_proposes_only_zero_budget_experiments_and_never_launches():
    result = analyze_marketing_campaigns([])
    assert all(x["budget_xof"] == 0 for x in result["zero_budget_experiments"])
    assert result["budget_authorized_for_spending"] is False


def test_rejects_non_https_source_reference():
    result = analyze_marketing_campaigns([campaign(source_ref="http://example.com")])
    assert result["campaigns_rejected"] == 1
