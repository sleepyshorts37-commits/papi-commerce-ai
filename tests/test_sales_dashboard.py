import pytest
from runtime.papi_core.sales_dashboard import build_sales_dashboard

def sales_snapshot():
    return {"as_of":"2026-11-12T12:00:00Z",
            "counts":{"valid":3,"rejected":0,"by_status":{"new":1,"won":1,"lost":1}},
            "queues":{"overdue_follow_ups":["P-1"],"follow_ups_due":[],"stale_7_days_or_more":["P-1"]},
            "conversion":{"won":1,"lost":1,"closed_count":2,"win_rate_percent":50.0}}

def test_dashboard_summarizes_pipeline_and_priorities():
    result = build_sales_dashboard(sales_snapshot())
    assert result["sales"]["valid_prospects"] == 3
    assert result["follow_ups"]["overdue_count"] == 1
    assert result["priorities"][0]["priority"] == "high"
    assert result["service_operations"] is None

def test_dashboard_includes_service_metrics():
    services = {"counts":{"requests":2,"quotes":1,"work_items":1,"payments":1,"rejected_records":0},
                "funnel":{"new_requests":1,"quotes_accepted":1,"work_in_progress":0,"work_delivered":1},
                "revenue":{"recognized_xof":10000,"verified_payment_count":1,"note":"Contrôle humain requis."}}
    result = build_sales_dashboard(sales_snapshot(), services)
    assert result["service_operations"]["recognized_revenue_xof"] == 10000
    assert result["service_operations"]["work_delivered"] == 1

def test_rejects_inconsistent_closed_count():
    snapshot = sales_snapshot()
    snapshot["conversion"]["closed_count"] = 5
    with pytest.raises(ValueError):
        build_sales_dashboard(snapshot)

def test_rejects_invalid_queue_shape():
    snapshot = sales_snapshot()
    snapshot["queues"]["overdue_follow_ups"] = 1
    with pytest.raises(ValueError):
        build_sales_dashboard(snapshot)

def test_dashboard_is_read_only():
    source = sales_snapshot()
    before = repr(source)
    result = build_sales_dashboard(source)
    assert repr(source) == before
    assert result["safety"]["read_only"] is True
    assert result["safety"]["messages_sent"] is False
