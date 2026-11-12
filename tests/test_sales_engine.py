from runtime.papi_core.sales_engine import analyze_sales_pipeline

NOW = "2026-11-12T12:00:00Z"

def prospect(pid="P-1", **overrides):
    row = {"prospect_id": pid, "source": "public_directory", "sector": "restaurant",
           "need_summary": "Réponses aux demandes clients", "status": "qualified",
           "service_code": "WHATSAPP_ASSISTANT_BASIC", "owner": "Moussa",
           "created_at": "2026-11-01T10:00:00Z", "updated_at": "2026-11-10T10:00:00Z",
           "next_follow_up_at": "2026-11-12T12:00:00Z"}
    row.update(overrides)
    return row

def test_due_and_stale_queues():
    result = analyze_sales_pipeline([prospect()], as_of=NOW)
    assert result["queues"]["follow_ups_due"] == ["P-1"]
    assert result["queues"]["stale_7_days_or_more"] == ["P-1"]

def test_overdue_follow_up():
    result = analyze_sales_pipeline([prospect(next_follow_up_at="2026-11-11T12:00:00Z")], as_of=NOW)
    assert result["queues"]["overdue_follow_ups"] == ["P-1"]

def test_closed_prospect_has_no_follow_up():
    result = analyze_sales_pipeline([prospect(status="won", next_follow_up_at=None)], as_of=NOW)
    assert result["conversion"]["win_rate_percent"] == 100

def test_duplicate_id_rejected():
    result = analyze_sales_pipeline([prospect(), prospect()])
    assert result["counts"]["valid"] == 1
    assert result["counts"]["rejected"] == 1

def test_personal_contact_field_rejected():
    result = analyze_sales_pipeline([prospect(phone="+221700000000")])
    assert result["counts"]["valid"] == 0

def test_win_rate_excludes_open_leads():
    result = analyze_sales_pipeline([
        prospect("P-1", status="won", next_follow_up_at=None),
        prospect("P-2", status="lost", next_follow_up_at=None),
        prospect("P-3", status="new")
    ], as_of=NOW)
    assert result["conversion"]["win_rate_percent"] == 50

def test_oversized_batch_rejected():
    import pytest
    with pytest.raises(ValueError):
        analyze_sales_pipeline([{}] * 501)
