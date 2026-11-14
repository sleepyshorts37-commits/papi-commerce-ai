# Day 2 — Shared snapshot API

Added migration 015 with papi_command_center_snapshot(limit). It aggregates counts and bounded recent records across workers/heartbeats, jobs, assignments, supervisor alerts and incidents, with outbox and approval status counters.

The function is stable, security-invoker and read-only. It validates a 1–100 record limit and is executable only by service_role. Payloads, private keys, approval identifiers and idempotency keys are not projected.
