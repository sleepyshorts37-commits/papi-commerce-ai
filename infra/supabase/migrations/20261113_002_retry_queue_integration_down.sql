-- Rollback 20261113_002: remove the retry-aware queue RPC overload.
-- Existing four-argument RPC is retained for compatibility with older clients.
BEGIN;

revoke all on function public.papi_fail_job(text, text, uuid, text, boolean, integer)
    from public, anon, authenticated;
drop function if exists public.papi_fail_job(text, text, uuid, text, boolean, integer);
grant execute on function public.papi_fail_job(text, text, uuid, text) to service_role;

COMMIT;
