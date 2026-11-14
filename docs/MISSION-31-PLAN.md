# Mission 31 — PAPI SHARED COMMAND CENTER

## Objective
Provide one authenticated, read-only operational snapshot across shared worker, job, assignment, supervisor, incident, outbox and approval registries. The local command center remains available; this mission adds a shared PostgreSQL read model without activating agents or workers.

## Five-day delivery
1. Inspect schemas; define contract, data classification and governance boundaries.
2. Implement a bounded, read-only snapshot API with operational summaries and sanitized recent records.
3. Add tests for aggregation, empty/filled states, pagination bounds and data minimization.
4. Integrate migration and contract tests into both disposable PostgreSQL CI paths; provide guarded rollback.
5. Document access, interpretation, limitations and handover; verify final commit and draft PR.

## Snapshot contract
- Summary counts for workers, tasks, jobs, supervisor alerts, incidents, outbox and approvals.
- Bounded recent lists for workers/heartbeats, jobs, assignments, alerts and incidents.
- generated_at timestamp for freshness; limit 1–100, default 20.
- No payloads, customer records, secrets, signing material, approval IDs, lease tokens or private idempotency keys.
- Service-role backend access only; browser clients receive no direct database privilege.

## Governance
- Read-only API: no worker status changes, assignments, queue claims, incident transitions, approval issuance/consumption or outbox delivery.
- No external messages, prospecting, publication, payments, purchases, paid services, remote migration or deployment.
- A service-role key stays in a trusted server secret store, never in a browser or repository.
- Existing department, agent roles, hierarchy, permissions and responsibilities remain unchanged.
- Shared snapshot is not operational until a Supabase test environment is explicitly configured and verified.

## Acceptance
- Migration 015 applies after migrations 001–014.
- Rollback removes only the new function and does not delete operational data.
- SQL contract test verifies summary counts, sanitized projections, bounds and least privilege.
- Both disposable PostgreSQL CI paths apply migration 015 and run its contract test.
- Final PR remains draft, open and unmerged.
