from runtime.papi_core.customer_service import analyze_customer_service


def ticket(**overrides):
    data = {
        "ticket_id": "T-001", "business_line": "PAPI MARKET", "channel": "whatsapp",
        "created_at": "2026-11-10T10:00:00Z", "updated_at": "2026-11-10T11:00:00Z",
        "status": "open", "category": "delivery_delay", "priority": "urgent",
        "order_ref": "ORD-001", "redacted_summary": "Le client signale un retard de livraison.",
    }
    data.update(overrides)
    return data


def test_triages_ticket_and_prepares_human_review_draft():
    result = analyze_customer_service([ticket()], as_of="2026-11-12T12:00:00Z")
    item = result["tickets"][0]
    assert item["human_review_required"] is True
    assert item["stale_update_detected"] is True
    assert "vérifions" in item["response_draft"]


def test_resolved_ticket_has_no_response_draft():
    result = analyze_customer_service([ticket(status="resolved")])
    assert result["tickets"][0]["response_draft"] is None


def test_rejects_personal_data_and_raw_message_fields():
    result = analyze_customer_service([ticket(phone="+221700000000")])
    assert result["tickets_rejected"] == 1


def test_rejects_duplicate_ticket_ids():
    result = analyze_customer_service([ticket(), ticket()])
    assert result["tickets_analyzed"] == 1
    assert result["tickets_rejected"] == 1


def test_rejects_naive_timestamps_and_invalid_priority():
    result = analyze_customer_service([ticket(created_at="2026-11-10T10:00:00"),
                                       ticket(ticket_id="T-002", priority="critical")])
    assert result["tickets_rejected"] == 2


def test_rejects_oversized_summary():
    result = analyze_customer_service([ticket(redacted_summary="x" * 501)])
    assert result["tickets_rejected"] == 1


def test_never_sends_customer_messages():
    result = analyze_customer_service([ticket()])
    assert result["read_only"] is True
    assert result["tickets"][0]["response_draft"]
    assert "messages_sent" not in result
