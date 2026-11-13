# Supabase versioned migrations

## Migration 20261113_001 — external audit checkpoint anchor

Files:
- `20261113_001_audit_anchor_up.sql`
- `20261113_001_audit_anchor_down.sql`

The up migration creates the immutable checkpoint record table, latest-head table,
immutability trigger and SECURITY DEFINER compare-and-swap RPC. It uses the same
schema contract as the corresponding section of `infra/supabase/schema.sql`.
It is wrapped in a transaction and is safe to re-apply to a database that already
has the baseline objects.

The down migration is intentionally **data-preserving by refusal**: it aborts
before dropping anything if either anchor table contains a row. Export and
independently retain audit evidence before considering any destructive retirement.
It does not drop the shared `pgcrypto` extension or `extensions` schema.

## Execution policy

1. Apply migrations in ascending version order, one file per transaction.
2. Record the applied version and checksum in the deployment system's migration
   ledger; this repository does not yet implement an automatic production runner.
3. Verify the checksum and inspect the target environment before applying.
4. Run the matching down migration only in a controlled maintenance window after
   confirming both tables are empty and evidence has been preserved.
5. Never execute migrations against production from CI. CI uses a separate,
   ephemeral PostgreSQL database and exercises up → down → up plus refusal on
   populated rollback.

The baseline `schema.sql` remains a fresh-install snapshot. Existing installations
should use the versioned migration rather than re-running the whole snapshot.
