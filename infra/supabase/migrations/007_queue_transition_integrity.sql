-- Day 2: preserve queue transition invariants and expose only generic error counts.
-- Error codes remain private; this function returns aggregates and booleans only.
create or replace function public.papi_complete_job(
    p_job_id text, p_worker_id text, p_lease_token uuid, p_result jsonb default '{}'::jsonb
) returns boolean
language plpgsql security invoker
set search_path = public, pg_temp
as $$
declare v_count integer;
begin
    if jsonb_typeof(p_result) <> 'object' then
        raise exception 'Invalid result object' using errcode = '22023';
    end if;
    update public.papi_jobs
       set status = 'done', result = p_result, last_error_code = null,
           updated_at = now(), lease_owner = null, lease_token = null, lease_until = null
     where id = p_job_id and status = 'running'
       and lease_owner = p_worker_id and lease_token = p_lease_token
       and lease_until > now();
    get diagnostics v_count = row_count;
    return v_count = 1;
end;
$$;

revoke all on function public.papi_complete_job(text, text, uuid, jsonb)
    from public, anon, authenticated;
grant execute on function public.papi_complete_job(text, text, uuid, jsonb)
    to service_role;

create or replace function public.papi_execution_queue_error_summary()
returns jsonb
language sql
stable
security invoker
set search_path = public, pg_temp
as $$
    select jsonb_build_object(
        'retry_with_error', count(*) filter (where status = 'retry' and last_error_code is not null),
        'retry_without_error', count(*) filter (where status = 'retry' and last_error_code is null),
        'failed_with_error', count(*) filter (where status = 'failed' and last_error_code is not null),
        'failed_without_error', count(*) filter (where status = 'failed' and last_error_code is null),
        'running_with_error', count(*) filter (where status = 'running' and last_error_code is not null),
        'done_with_error', count(*) filter (where status = 'done' and last_error_code is not null)
    )
    from public.papi_jobs;
$$;

revoke all on function public.papi_execution_queue_error_summary()
    from public, anon, authenticated;
grant execute on function public.papi_execution_queue_error_summary()
    to service_role;
