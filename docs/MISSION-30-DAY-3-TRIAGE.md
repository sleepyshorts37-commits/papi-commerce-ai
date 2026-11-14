# Day 3 — Qualification and treatment

Implemented papi_incident_open_from_alert():
- Locks and validates the source alert.
- Uses an advisory transaction lock for the incident key.
- Prevents duplicate incidents for the same source alert.
- Returns the existing incident on an identical replay.
- Maps alert type and severity into incident category and severity.
- Writes the creation event and audit record in the same transaction.

Implemented papi_incident_transition() with explicit state-transition validation, human assignment, evidence capture, severity escalation, resolution and closure requirements. Event keys support safe retry handling.
