from runtime.papi_core.order_management import analyze_orders


def order(**overrides):
    data = {
        "order_id": "ORD-001", "business_line": "PAPI MARKET", "channel": "whatsapp",
        "created_at": "2026-11-10T10:00:00Z", "updated_at": "2026-11-10T11:00:00Z",
        "status": "processing", "expected_delivery_at": "2026-11-11T10:00:00Z",
        "payment_evidence_status": "declared_paid", "total_xof": 12000, "currency": "XOF",
        "items": [{"sku": "SKU-1", "quantity": 2}],
    }
    data.update(overrides)
    return data


def test_detects_overdue_and_stale_orders():
    result = analyze_orders([order()], as_of="2026-11-12T12:00:00Z")
    assert result["orders_analyzed"] == 1
    assert result["overdue_orders"] == ["ORD-001"]
    assert result["stale_orders"] == ["ORD-001"]


def test_delivered_order_is_not_overdue():
    result = analyze_orders([order(status="delivered", updated_at="2026-11-10T13:00:00Z", delivered_at="2026-11-10T12:00:00Z")],
                            as_of="2026-11-12T12:00:00Z")
    assert result["overdue_orders"] == []


def test_rejects_personal_data_fields():
    result = analyze_orders([order(phone="+221700000000")])
    assert result["orders_rejected"] == 1


def test_rejects_duplicate_order_ids():
    result = analyze_orders([order(), order()])
    assert result["orders_analyzed"] == 1
    assert result["orders_rejected"] == 1


def test_rejects_naive_timestamp_and_wrong_currency():
    result = analyze_orders([order(created_at="2026-11-10T10:00:00"),
                             order(order_id="ORD-002", currency="EUR")])
    assert result["orders_rejected"] == 2


def test_rejects_delivered_without_delivery_timestamp():
    result = analyze_orders([order(status="delivered")])
    assert result["orders_rejected"] == 1


def test_rejects_invalid_quantity():
    result = analyze_orders([order(items=[{"sku": "SKU-1", "quantity": 0}])])
    assert result["orders_rejected"] == 1


def test_is_strictly_read_only():
    result = analyze_orders([order()])
    assert result["read_only"] is True
    assert "writes_performed" not in result
