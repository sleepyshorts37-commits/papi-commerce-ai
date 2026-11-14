# Day 2 — Incident register

Added migration 014 with:
- papi_incidents: unique incident key, source alert, optional worker/job links, category, severity, state, evidence, human assignee, SLA target and resolution metadata.
- papi_incident_events: append-only history with actor, transition, evidence and timestamp.
- Partial query indexes for active workflow, worker history and human assignment.
- RLS, revoked client privileges and service-role read access.
- Trigger protection against incident-event UPDATE and DELETE.
- A rollback script that refuses to destroy non-empty incident history.
