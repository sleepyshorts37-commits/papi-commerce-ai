# Day 1 — Audit et contrats

Reviewed the local memory/chat modules, principal sealing, SupabaseStore and shared-collaboration migrations 004/005. The database already has append-only tables, unique idempotency keys and keyset indexes; Python memory and chat APIs remain local by default.

Defined explicit server-store methods. Every remote write requires a sealed authenticated-agent principal whose agent ID matches the event actor or chat sender. Reads are bounded and actor-filtered. The service-role credential remains a trusted backend boundary, not an agent identity token.
