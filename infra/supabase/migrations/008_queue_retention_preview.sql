-- Day 3: retention preview only. This function never deletes or updates records.
create or replace function public.papi_execution_queue_retention_preview(
    p_cutoff timestamptz
) returns jsonb
language plpgsql
stable
security invoker
set search_path = public, pg_temp
as $$
declare
    v_summary jsonb;
begin
    if p_cutoff is null or p_cutoff >= now() then
        raise exception 'Retention cutoff must be in the past' using errcode = '22023';
    end if;

    select jsonb_build_object(
        'preview_only', true,
        'eligible_done', count(*) filter (
            where status = 'done' and created_at <= p_cutoff
        ),
        'eligible_failed', count(*) filter (
            where status = 'failed' and created_at <= p_cutoff
        ),
        'protected_running', count(*) filter (where status = 'running'),
        'protected_queued_or_retry', count(*) filter (
            where status in ('queued', 'retry')
        ),
        'protected_recent_terminal', count(*) filter (
            where status in ('done', 'failed') and created_at > p_cutoff
        )
    )
    into v_summary
    from public.papi_jobs;

    return v_summary;
end;
$$;

revoke all on function public.papi_execution_queue_retention_preview(timestamptz)
    from public, anon, authenticated;
grant execute on function public.papi_execution_queue_retention_preview(timestamptz)
    to service_role;
