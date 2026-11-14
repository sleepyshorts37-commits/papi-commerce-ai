# Mission 30 — PAPI INCIDENT RESPONSE & RECOVERY

## Objective
Provide a governed internal incident register that converts supervisor alerts into trackable incidents and records human-led triage, ownership, escalation, mitigation, resolution and closure.

## Five-day plan
1. Architecture, severity model, lifecycle and autonomy boundaries.
2. Incident and append-only event registers, source links, SLA targets and rollback.
3. Idempotent alert conversion and validated lifecycle transitions.
4. Human ownership, severity escalation, overdue detection and audit.
5. PostgreSQL contracts, least privilege, CI, documentation and closure.

## Severity targets
- Critical: 1 hour.
- High: 4 hours.
- Medium: 24 hours.
- Low: 72 hours.

These are internal target windows, not guarantees. An overdue detector records a breach and audit event; it does not execute remediation.

## Lifecycle
open → qualified → investigating → mitigated → resolved → closed.
Reopening is permitted from resolved to investigating. Invalid transitions are rejected. Closing requires prior resolution and a meaningful closure summary.

## Governance
- Incidents are assigned only to named human identities.
- Alert-to-incident conversion is idempotent.
- Incident events are append-only.
- Only service-role RPCs can mutate records; the trusted backend must authenticate the human actor before passing actor IDs.
- No worker activation, pause, disablement, permission changes, external communications, customer contact, spending, publishing, production migration or deployment.
- Rollback refuses to delete incident history.
