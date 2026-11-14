# Day 1 — Architecture and data contract

Reviewed local command-center documentation and shared PostgreSQL schema through Mission 30. Worker, job, assignment, heartbeat, alert, incident, outbox and approval records already exist, but no single shared read model exposes a bounded operational snapshot.

Defined a service-role-only, read-only JSON contract. The projection excludes job payloads, agent identity documents, signing material, approval identifiers, lease tokens and private idempotency keys. It performs no mutation and does not imply that a Supabase project is configured.
