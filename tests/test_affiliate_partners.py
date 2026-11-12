from runtime.papi_core.affiliate_partners import analyze_affiliate_partners


def referral(**overrides):
    data = {
        "partner_id": "PARTNER-001", "referral_id": "REF-001", "sale_id": "SALE-001",
        "business_line": "PAPI MARKET", "channel": "whatsapp",
        "referred_at": "2026-11-01T10:00:00Z", "sale_at": "2026-11-03T12:00:00Z",
        "referral_status": "converted", "sale_status": "paid", "order_value_xof": 25000,
        "commission_rate_bps": 500, "payment_evidence_status": "provider_confirmed",
    }
    data.update(overrides)
    return data


def test_calculates_provisional_commission_only_for_marked_paid_sale():
    result = analyze_affiliate_partners([referral()])
    item = result["commission_records"][0]
    assert item["commission_estimate_xof"] == 1250
    assert item["commission_estimate_is_provisional"] is True
    assert result["payouts_executed"] == 0


def test_unverified_or_pending_sale_has_no_commission_estimate():
    result = analyze_affiliate_partners([
        referral(payment_evidence_status="declared"),
        referral(referral_id="REF-002", sale_id="SALE-002", sale_status="pending",
                 referral_status="qualified", payment_evidence_status="unknown"),
    ])
    assert all(row["commission_estimate_xof"] is None for row in result["commission_records"])


def test_rejects_personal_data_and_unknown_fields():
    result = analyze_affiliate_partners([referral(partner_phone="+221700000000")])
    assert result["records_rejected"] == 1


def test_rejects_duplicate_referral_and_sale_ids():
    result = analyze_affiliate_partners([referral(), referral()])
    assert result["records_analyzed"] == 1
    assert result["records_rejected"] == 1


def test_rejects_invalid_rate_and_negative_amount():
    result = analyze_affiliate_partners([
        referral(commission_rate_bps=10001),
        referral(referral_id="REF-002", sale_id="SALE-002", commission_rate_bps=-1),
    ])
    assert result["records_rejected"] == 2


def test_requires_timezone_aware_timestamps_and_consistent_sale_status():
    result = analyze_affiliate_partners([
        referral(referred_at="2026-11-01T10:00:00"),
        referral(referral_id="REF-002", sale_id="SALE-002", sale_status="none",
                 referral_status="converted", order_value_xof=0),
    ])
    assert result["records_rejected"] == 2


def test_partner_summary_and_no_external_actions():
    result = analyze_affiliate_partners([referral()])
    summary = result["partner_summary"]["PARTNER-001"]
    assert summary["converted_referrals"] == 1
    assert summary["provisional_commission_estimate_xof"] == 1250
    assert result["partner_contacts_sent"] == 0
