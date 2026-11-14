# Day 4 — CI and rollback

Added a guarded rollback that drops only the Mission 31 function and preserves all operational records. Both disposable PostgreSQL CI paths apply migration 015 and run the new contract test after migrations 001–014.

No remote Supabase project is contacted, no production migration is applied and no worker or queue consumer is started.
