# Worker audit integration — design and release gate

## Status

Implementation present in this PR; release validation is still pending. The worker remains disabled by policy in production. This document does not deploy a worker, activate agents, or authorize external actions.

## Trust boundary

- Never accept an actor name from the job payload, task payload, handler context supplied by a caller, or a caller-provided string.
- A pre-authentication event such as `job.claimed` uses a fixed system actor derived from the configured worker identity (for example `system:worker:<worker_id>`). It must not name the claimed agent as authenticated.
- Agent-attributed events are emitted only after `authorize_authenticated_agent(...)` succeeds and the returned sealed principal is checked against the expected agent. The actor comes from that principal, never from `task.owner_agent` alone.
- Do not put signed envelopes, signatures, nonce values, lease tokens, payloads, customer data, email addresses, phone numbers, credentials, or message bodies in audit details.

## Event lifecycle

Use a deterministic, bounded event ID derived from the job ID and event name (hash the raw job ID before constructing the ID if necessary). This makes retries idempotent without exposing arbitrary job identifiers.

1. `job.claimed` — after a valid claim, attributed to the system worker.
2. `job.authentication_blocked` — when identity verification or authorization fails; system worker actor only because no authenticated principal exists.
3. `job.handler_started` — after cryptographic authentication and permission checks, immediately before handler execution; authenticated agent actor.
4. Exactly one terminal outcome where known:
   - `job.completed` — only after the queue confirms completion with the matching lease.
   - `job.blocked` — for a post-authentication permission/policy block, with authenticated agent actor only if authentication had already succeeded; otherwise system worker actor.
   - `job.failed` — for validation or handler failure, using the authenticated agent actor only if authentication succeeded.
   - `job.lease_lost` — system worker actor; do not claim successful completion.

Each event contains only bounded metadata: event name, job/task opaque identifier or digest, handler name from the registered handler, outcome code, and worker identifier. No arbitrary handler result or exception text.

## Integrity limits and external anchoring

The SHA-256 chain detects accidental corruption and partial or local edits that leave an inconsistent chain. It is **not tamper-proof against an attacker who can rewrite the entire journal**, because that attacker can recompute every subsequent hash. The current implementation has no external trusted checkpoint, remote append-only store, or independently protected HMAC key. Do not describe this local journal as immutable or independently non-repudiable.

The helper in `runtime/papi_core/audit_checkpoint.py` exports a versioned checkpoint (`schema_version`, `sequence`, `head_hash`) and verifies that a local journal still contains the externally checkpointed prefix. It reports the number of local events after that checkpoint as an unanchored suffix. It does not publish, retrieve, authenticate, or persist checkpoints. `verify_checkpoint_transition(previous, current)` rejects sequence rollback and conflicting hashes at an identical sequence. **It does not prove that a later checkpoint is a cryptographic extension of an earlier checkpoint**: two independently constructed checkpoints with increasing sequence numbers can still describe divergent histories. The external store must therefore accept updates only from a trusted publisher that derives each checkpoint from a locally verified journal, use an atomic compare-and-swap against the previously stored checkpoint, and authenticate stored records. If untrusted publishers must be supported, add a verifiable consistency proof before accepting a forward transition.

Before production use for high-assurance evidence, connect this helper to an independently controlled checkpoint mechanism (for example, periodically publish the latest sequence number and event hash to a separately permissioned append-only service). Protect checkpoint credentials outside the worker process, authenticate retrieved checkpoints, enforce monotonic checkpoint sequence numbers at the external service, define recovery and verification procedures, and alert on missing or rolled-back checkpoints. This is a release blocker for any requirement that assumes resistance to a privileged local file attacker.

Audit input is bounded before persistence: nested details are limited to depth 8, each list/object to 100 entries, individual strings to 500 characters, integers to 63 bits, and each serialized event to 64 KiB. These limits reduce memory/CPU abuse and prevent a single event from consuming unbounded journal space.

A truncated or malformed record is fail-closed: readers and subsequent appends must reject the journal rather than silently discard or repair the tail.

## Audit failure policy

- Before handler execution, failure to append `job.handler_started` is **fail-closed**: do not invoke the handler; fail or release the job using its valid lease and return a controlled audit error.
- A terminal audit append occurs after the queue's durable terminal transition. It is **best-effort** because the business outcome cannot safely be rolled back after completion or a handler side effect. Record a local operational alert on append failure, without changing the already committed job result.
- Never report an event as recorded unless `append_event` returned successfully.
- Audit errors must not expose sensitive exception content to queue error codes or public results.

## Required tests before implementation can be accepted

- No claim when execution policy is disabled.
- No agent-attributed event before cryptographic authentication.
- Forged `owner_agent`, actor, handler context, and job payload values cannot influence the audit actor.
- Authentication failure records only a system actor. Post-authentication policy blocks are attributed to the sealed authenticated principal.
- Successful authentication binds every agent event to the authenticated principal.
- Audit failure before handler start prevents handler invocation.
- Terminal audit failure does not rewrite a successfully committed queue outcome.
- Lease loss cannot produce `job.completed`.
- Retry/idempotency produces no duplicate event IDs.
- Concurrent workers and expired leases do not create contradictory terminal outcomes.
- Sensitive fields and raw exceptions never enter the journal.

## Dependency and rollout order

PR #84 is integrated into this branch. The worker passes the exact principal returned by the cryptographic authorization boundary to handlers; it does not construct an alternate principal.

The current tests cover disabled execution, handler execution, unknown handlers, lease loss, pre-handler audit failure, and best-effort terminal audit failure. Additional release tests are still required for forged actor fields, authentication failure attribution, retry/concurrency behavior, expired leases, and sensitive-data exclusion across the complete worker lifecycle. Keep `execution_enabled=false`, `external_actions_enabled=false`, and financial/legal permissions disabled throughout review. Do not merge or deploy until CI and independent review are complete.
