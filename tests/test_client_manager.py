import pytest
from runtime.papi_core.client_manager import analyze_client_experience

NOW = "2026-11-12T12:00:00Z"

def case(case_id="C-1", **overrides):
    row = {"case_id": case_id, "client_ref": "CLIENT-ANON-01",
           "service_code": "WHATSAPP_ASSISTANT_BASIC", "category": "support",
           "summary": "Question sur le fonctionnement du service", "status": "open",
           "created_at": "2026-11-10T10:00:00Z", "updated_at": "2026-11-11T10:00:00Z"}
    row.update(overrides)
    return row

def feedback(feedback_id="F-1", **overrides):
    row = {"feedback_id": feedback_id, "client_ref": "CLIENT-ANON-01",
           "case_id": "C-1", "rating": 4, "comment": "Service satisfaisant",
           "status": "received", "created_at": "2026-11-11T10:00:00Z",
           "updated_at": "2026-11-11T10:00:00Z"}
    row.update(overrides)
    return row

def test_open_case_and_feedback_queues():
    result = analyze_client_experience([case()], [feedback()], as_of=NOW)
    assert result["cases"]["open_case_ids"] == ["C-1"]
    assert result["feedback"]["unresolved_feedback_ids"] == ["F-1"]
    assert result["feedback"]["average_rating"] == 4

def test_resolved_case_requires_timestamp():
    result = analyze_client_experience([case(status="resolved")], [], as_of=NOW)
    assert result["cases"]["valid"] == 0
    assert result["rejected"][0]["category"] == "case"

def test_resolved_case_with_timestamp():
    result = analyze_client_experience([
        case(status="resolved", resolved_at="2026-11-11T11:00:00Z")
    ], [], as_of=NOW)
    assert result["cases"]["by_status"]["resolved"] == 1

def test_personal_contact_field_rejected():
    result = analyze_client_experience([case(phone="+221700000000")], [])
    assert result["cases"]["valid"] == 0

def test_feedback_requires_known_case_reference():
    result = analyze_client_experience([], [feedback()])
    assert result["feedback"]["valid"] == 0

def test_service_satisfaction_metrics():
    metrics = [{"service_code":"WHATSAPP_ASSISTANT_BASIC","delivery_count":10,
                "satisfaction_total":42,"satisfaction_count":10,"complaint_count":2}]
    result = analyze_client_experience([], [], metrics, as_of=NOW)
    assert result["service_metrics"][0]["average_rating"] == 4.2
    assert result["service_metrics"][0]["complaint_rate_percent"] == 20.0

def test_duplicate_case_rejected():
    result = analyze_client_experience([case(), case()], [])
    assert result["cases"]["valid"] == 1
    assert len(result["rejected"]) == 1

def test_no_external_actions():
    result = analyze_client_experience([], [])
    assert result["safety"]["read_only"] is True
    assert result["safety"]["messages_sent"] is False
    assert result["safety"]["budget_xof"] == 0
