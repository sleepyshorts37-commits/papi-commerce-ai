from copy import deepcopy

import pytest

from runtime.papi_core.audit import validate_event
from runtime.papi_core.incident_bridge import (
    IncidentBridgeError,
    build_incident_report_candidates,
)


AS_OF = "2026-11-12T10:00:00Z"


def issue(code, scope, severity, subject="worker-01"):
    return {"code": code, "scope": scope, "severity": severity,
            "subject_id": subject, "action_executed": False}


def report(issues):
    return {"as_of": AS_OF, "issues": issues, "read_only": True}


@pytest.mark.parametrize("code,scope,severity,category", [
    ("worker_offline", "worker", "critical", "worker"),
    ("worker_suspended", "worker", "warning", "worker"),
    ("worker_status_unknown", "worker", "warning", "worker"),
    ("identity_invalid_or_permissions_mismatch", "worker", "critical", "security"),
    ("heartbeat_unverified", "worker", "warning", "worker"),
    ("heartbeat_stale", "worker", "critical", "worker"),
    ("lease_expired", "job", "critical", "job"),
    ("retry_exhausted", "job", "critical", "job"),
    ("repeated_failures", "job", "warning", "job"),
])
def test_known_issue_maps_to_valid_incident_event(code, scope, severity, category):
    result = build_incident_report_candidates(report([issue(code, scope, severity)]))
    assert result["summary"]["candidates"] == 1
    event = result["report_candidates"][0]["event"]
    validate_event(event)
    assert event["action"] == "incident.reported"
    assert event["details"]["category"] == category
    assert result["events_appended"] == 0


def test_unknown_issue_is_skipped_without_copying_payload():
    result = build_incident_report_candidates(report([
        {"code": "unrecognized", "scope": "other", "subject_id": "x",
         "secret": "must-not-leak"}
    ]))
    assert result["report_candidates"] == []
    assert result["summary"]["unknown_issues_skipped"] == 1


def test_same_snapshot_produces_stable_ids():
    source = report([issue("worker_offline", "worker", "critical")])
    first = build_incident_report_candidates(source)
    second = build_incident_report_candidates(source)
    assert first == second


def test_input_is_not_mutated_and_preview_is_read_only():
    source = report([issue("lease_expired", "job", "critical", "job-7")])
    original = deepcopy(source)
    result = build_incident_report_candidates(source)
    assert source == original
    assert result["read_only"] is True
    assert result["writes_performed"] == result["events_appended"] == 0


@pytest.mark.parametrize("source", [
    None,
    {"as_of": AS_OF, "issues": [], "read_only": False},
    {"as_of": "2026-11-12T10:00:00", "issues": [], "read_only": True},
    {"as_of": AS_OF, "issues": "invalid", "read_only": True},
    report([issue("worker_offline", "job", "critical")]),
    report([issue("worker_offline", "worker", "warning")]),
    report([dict(issue("worker_offline", "worker", "critical"), action_executed=True)]),
])
def test_invalid_source_fails_closed(source):
    with pytest.raises(IncidentBridgeError):
        build_incident_report_candidates(source)


def test_sensitive_or_untrusted_source_text_is_not_copied():
    source = report([dict(issue("worker_offline", "worker", "critical"),
                          recommended_action="token=private", raw_payload="secret")])
    event = build_incident_report_candidates(source)["report_candidates"][0]["event"]
    assert "token" not in str(event).lower()
    assert "private" not in str(event)
    assert "secret" not in str(event)
