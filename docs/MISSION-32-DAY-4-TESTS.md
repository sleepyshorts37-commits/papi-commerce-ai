# Day 4 — Tests and integration

Added mocked PostgREST tests for normalized memory writes, idempotent duplicates, actor mismatch rejection, chat sender authentication and keyset cursor progression.

Added migration 016, a rollback that removes only its read function, and SQL contract tests for shared/private memory isolation, visible supersede history, keyset pagination, invalid partial cursors and least-privilege grants. Both disposable PostgreSQL CI paths apply the migration and execute the contract test.

No real Supabase project is contacted.
