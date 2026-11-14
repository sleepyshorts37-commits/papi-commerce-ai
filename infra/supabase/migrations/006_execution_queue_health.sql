-- Aggregate operational health only: never expose job IDs, payloads, results or lease tokens.
create or replace function public.papi_execution_queue_health()
returns jsonb
language sql
stable
security invoker
set search_path = public, pg_temp
as $$
    select jsonb_build_object(
        'queued', count(*) filter (where status = 'queued'),
        'retry', count(*) filter (where status = 'retry'),
        'running', count(*) filter (where status = 'running'),
        'done', count(*) filter (where status = 'done'),
        'failed', count(*) filter (where status = 'failed'),
        'expired_leases', count(*) filter (
            where status = 'running' and lease_until < now()
        ),
        'ready_waiting', count(*) filter (
            where status in ('queued', 'retry') and available_at <= now()
        ),
        'oldest_ready_age_seconds', coalesce(
            floor(extract(epoch from (now() - min(created_at) filter (
                where status in ('queued', 'retry') and available_at <= now()
            ))))::bigint, 0
        )
    )
    from public.papi_jobs;
$$;

revoke all on function public.papi_execution_queue_health() from public, anon, authenticated;
grant execute on function public.papi_execution_queue_health() to service_role;
