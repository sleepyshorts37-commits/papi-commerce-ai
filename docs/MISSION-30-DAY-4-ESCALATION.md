# Day 4 — Escalation and recovery

Implemented human ownership, severity escalation and SLA target recalculation. The overdue detector marks each breach once, appends an immutable event and writes an audit record. It does not automatically assign, suspend, disable or restart workers.

Resolution requires a meaningful summary and evidence. Closure is permitted only after resolution and also requires a summary. Reopening is permitted from resolved to investigating and establishes a fresh SLA window.
