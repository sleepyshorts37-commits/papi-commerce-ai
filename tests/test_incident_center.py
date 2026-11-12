import unittest

from papi_core.incident_center import IncidentCenterError, build_incident_center


def event(event_id, action, incident_id="INC-1", details=None):
    return {
        "event_id": event_id, "occurred_at": "2026-11-12T10:00:00Z",
        "actor": "astou", "action": action, "entity_type": "incident",
        "entity_id": incident_id, "details": details or {},
    }


class IncidentCenterTests(unittest.TestCase):
    def report(self, **overrides):
        details = {
            "severity": "critical", "category": "worker",
            "summary": "Worker sans heartbeat",
            "recommendation": "Vérifier la connexion et les journaux.",
        }
        details.update(overrides)
        return event("E-1", "incident.reported", details=details)

    def test_reported_incident_is_open(self):
        result = build_incident_center([self.report()])
        self.assertEqual(result["summary"]["by_status"]["open"], 1)
        self.assertEqual(result["summary"]["active_by_severity"]["critical"], 1)
        self.assertTrue(result["read_only"])

    def test_acknowledgement_and_resolution_are_append_only_projection(self):
        result = build_incident_center([
            self.report(),
            event("E-2", "incident.acknowledged"),
            event("E-3", "incident.resolved"),
        ])
        self.assertEqual(result["incidents"][0]["status"], "resolved")
        self.assertEqual(len(result["incidents"][0]["history"]), 3)
        self.assertEqual(result["writes_performed"], 0)

    def test_duplicate_report_is_rejected(self):
        with self.assertRaises(IncidentCenterError):
            build_incident_center([self.report(), self.report()])

    def test_transition_without_report_is_rejected(self):
        with self.assertRaises(IncidentCenterError):
            build_incident_center([event("E-2", "incident.resolved")])

    def test_transition_after_resolution_is_rejected(self):
        with self.assertRaises(IncidentCenterError):
            build_incident_center([
                self.report(), event("E-2", "incident.resolved"),
                event("E-3", "incident.acknowledged"),
            ])

    def test_invalid_severity_is_rejected(self):
        with self.assertRaises(IncidentCenterError):
            build_incident_center([self.report(severity="emergency")])

    def test_non_incident_events_are_ignored(self):
        ordinary = event("E-4", "task.updated", incident_id="T-1")
        result = build_incident_center([ordinary])
        self.assertEqual(result["summary"]["total"], 0)

    def test_transition_cannot_change_details(self):
        with self.assertRaises(IncidentCenterError):
            build_incident_center([
                self.report(),
                event("E-2", "incident.acknowledged", details={"severity": "info"}),
            ])


if __name__ == "__main__":
    unittest.main()
