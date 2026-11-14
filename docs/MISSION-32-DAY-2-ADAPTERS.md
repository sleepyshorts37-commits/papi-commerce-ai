# Day 2 — Supabase adapters

Added explicit SupabaseStore operations to append memory events and chat messages with deterministic SHA-256 idempotency keys. Memory source fields are mapped to normalized SQL columns; chat messages are validated against the existing local schema before publication.

A repeated idempotency key is reported as a duplicate rather than creating a second record. No local API defaults were changed and no network call occurs unless the explicit adapter method is invoked.
